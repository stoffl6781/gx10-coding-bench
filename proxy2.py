"""Pass-through proxy between opencode and a model server.

- overrides "model" and merges extra body fields (e.g. chat_template_kwargs) per benchmark config
- mirrors assistant "reasoning" into "reasoning_content" so llama.cpp sees it as well
- logs one JSON line per chat request: tokens, TTFT, duration, tool calls
Usage: proxy2.py <port> <upstream host:port> <model> <inject-json> <log>
"""
import http.client
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, UP, MODEL, INJECT, LOG = int(sys.argv[1]), sys.argv[2].split(":"), sys.argv[3], json.loads(sys.argv[4]), sys.argv[5]


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        c = http.client.HTTPConnection(UP[0], int(UP[1]), timeout=60)
        c.request("GET", self.path)
        r = c.getresponse()
        data = r.read()
        self.send_response(r.status)
        self.send_header("Content-Type", r.getheader("Content-Type", "application/json"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        body["model"] = MODEL
        body.update(INJECT)
        for m in body.get("messages", []):
            if m.get("role") == "assistant" and m.get("reasoning") and not m.get("reasoning_content"):
                m["reasoning_content"] = m["reasoning"]
        is_title = "title generator" in json.dumps(body.get("messages", [{}])[0])[:400]
        raw = json.dumps(body).encode()
        t0 = time.time()
        c = http.client.HTTPConnection(UP[0], int(UP[1]), timeout=3600)
        c.request("POST", self.path, body=raw, headers={"Content-Type": "application/json"})
        r = c.getresponse()
        self.send_response(r.status)
        self.send_header("Content-Type", r.getheader("Content-Type", "text/event-stream"))
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        ttft, usage, tools, buf = None, {}, 0, b""
        while True:
            chunk = r.read1(65536)
            if not chunk:
                break
            self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
            self.wfile.flush()
            buf += chunk
            *lines, buf = buf.split(b"\n")
            for ln in lines:
                if not ln.startswith(b"data: {"):
                    continue
                d = json.loads(ln[6:])
                if d.get("usage"):
                    usage = d["usage"]
                for ch in d.get("choices", []):
                    delta = ch.get("delta", {})
                    if ttft is None and (delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content") or delta.get("tool_calls")):
                        ttft = time.time() - t0
                    for tc in delta.get("tool_calls") or []:
                        if tc.get("id"):
                            tools += 1
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": t0, "title": is_title, "status": r.status,
                                "prompt_tokens": usage.get("prompt_tokens"),
                                "completion_tokens": usage.get("completion_tokens"),
                                "ttft": ttft, "secs": time.time() - t0, "tool_calls": tools}) + "\n")

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
