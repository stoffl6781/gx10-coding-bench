"""Raw throughput of one OpenAI-compatible endpoint: prefill tok/s and single-stream decode tok/s.

Usage: speed_test.py <host:port> <model>
"""
import json
import random
import sys
import time
import urllib.request

URL = f"http://{sys.argv[1]}/v1/chat/completions"
MODEL = sys.argv[2]
WORDS = "haus baum code server modell rechnung kunde datei test fehler wert liste zahl tabelle text".split()


def stream(messages, max_tokens, extra=None):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "stream": True,
            "stream_options": {"include_usage": True}, **(extra or {})}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0, ttft, usage = time.time(), None, {}
    with urllib.request.urlopen(req, timeout=1800) as r:
        for line in r:
            if not line.startswith(b"data: {"):
                continue
            d = json.loads(line[6:])
            usage = d.get("usage") or usage
            for ch in d.get("choices", []):
                delta = ch.get("delta", {})
                if ttft is None and (delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content")):
                    ttft = time.time() - t0
    return ttft, time.time() - t0, usage


# prefill: unique random prompt so nothing comes from the prefix cache
for n_words in (4000, 12000):
    rnd = random.Random(time.time())
    text = " ".join(rnd.choice(WORDS) + str(rnd.randint(0, 99)) for _ in range(n_words))
    ttft, total, u = stream([{"role": "user", "content": text + "\nAntworte nur mit OK."}], 1,
                            {"chat_template_kwargs": {"enable_thinking": False}})
    print(f"prefill {u.get('prompt_tokens')} tok: {total:5.1f} s = {u.get('prompt_tokens', 0) / total:6.0f} tok/s", flush=True)

# decode: one long code answer, three repetitions
for i in range(3):
    ttft, total, u = stream([{"role": "user", "content": "Schreib ein vollständiges Python-Modul für eine "
                              "Lagerverwaltung mit Klassen, Docstrings und Tests. Nur Code."}], 1200,
                            {"chat_template_kwargs": {"enable_thinking": False}})
    out = u.get("completion_tokens", 0)
    print(f"decode run {i + 1}: {out} tok in {total - ttft:5.1f} s = {out / (total - ttft):5.1f} tok/s (TTFT {ttft:.2f} s)",
          flush=True)
