"""Runs the multi-turn opencode coding tasks against one model config and grades them with hidden tests.

python3 run_bench.py --name qwen36-on --upstream <host>:8000 --model qwen3.6-35b-a3b \
    --inject '{"chat_template_kwargs": {"preserve_thinking": true}}' --runs 3
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 8800

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--upstream", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--inject", default="{}")
ap.add_argument("--runs", type=int, default=3)
ap.add_argument("--tasks", default="pricing,bookings")
ap.add_argument("--turn-timeout", type=int, default=2400)
a = ap.parse_args()

cfg = HERE / "opencode-bench.json"
cfg.write_text(json.dumps({
    "$schema": "https://opencode.ai/config.json",
    "provider": {"bench": {"name": "bench", "npm": "@ai-sdk/openai-compatible",
                           "options": {"baseURL": f"http://127.0.0.1:{PORT}/v1"},
                           "models": {"m": {"name": "bench", "limit": {"context": 131072, "output": 32768}}}}},
}))
# DECISION: workdirs live outside bench/, so an agent exploring parent dirs cannot find seeds or hidden tests
out_dir = HERE.parent / "ocruns" / a.name
out_dir.mkdir(parents=True, exist_ok=True)
req_log = out_dir / "requests.jsonl"
proxy = subprocess.Popen([sys.executable, str(HERE / "proxy2.py"), str(PORT), a.upstream, a.model, a.inject, str(req_log)])
time.sleep(1)
env = dict(os.environ, OPENCODE_CONFIG=str(cfg))


def requests_between(t0, t1):
    if not req_log.exists():
        return []
    rows = [json.loads(l) for l in req_log.read_text().splitlines() if l.strip()]
    return [r for r in rows if t0 <= r["ts"] <= t1 and not r["title"]]


try:
    for run in range(1, a.runs + 1):
        for task in a.tasks.split(","):
            tdir = HERE / "tasks" / task
            wd = out_dir / f"{task}-{run}"
            shutil.rmtree(wd, ignore_errors=True)
            if (tdir / "seed").exists():
                shutil.copytree(tdir / "seed", wd)
            else:
                wd.mkdir(parents=True)
            # DECISION: a git repo per workdir makes it its own opencode project, so --continue stays inside this run
            subprocess.run(["git", "init", "-q"], cwd=wd)
            subprocess.run(["git", "add", "-A"], cwd=wd)
            subprocess.run(["git", "-c", "user.email=b@b", "-c", "user.name=b", "commit", "-qm", "seed", "--allow-empty"], cwd=wd)
            turns_out, t_start = [], time.time()
            for i, msg in enumerate(json.loads((tdir / "turns.json").read_text())):
                # DECISION: --standalone, the shared background service keeps the config it was started with
                cmd = ["opencode", "run", "--standalone", "--auto", "-m", "bench/m"] + (["-c"] if i else []) + [msg]
                t = time.time()
                try:
                    # DECISION: opencode --standalone takes its project dir from $PWD, not from the process cwd
                    p = subprocess.run(cmd, cwd=wd, env=dict(env, PWD=str(wd)), capture_output=True, text=True,
                                       timeout=a.turn_timeout)
                    code = p.returncode
                    (wd.parent / f"{task}-{run}.turn{i + 1}.log").write_text(p.stdout + p.stderr)
                except subprocess.TimeoutExpired:
                    code = "timeout"
                turns_out.append({"secs": round(time.time() - t), "exit": code})
            t_end = time.time()
            graded = json.loads(subprocess.run([sys.executable, "-I", str(tdir / "hidden_test.py"), str(wd)],
                                               capture_output=True, text=True, timeout=120).stdout or
                                '{"passed":0,"total":0,"failed":["grader crashed"]}')
            reqs = requests_between(t_start, t_end)
            ttfts = [r["ttft"] for r in reqs if r["ttft"]]
            row = {"config": a.name, "task": task, "run": run, **graded, "turns": turns_out,
                   "wall": round(t_end - t_start), "requests": len(reqs),
                   "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in reqs),
                   "completion_tokens": sum(r["completion_tokens"] or 0 for r in reqs),
                   "max_prompt": max([r["prompt_tokens"] or 0 for r in reqs] or [0]),
                   "tool_calls": sum(r["tool_calls"] for r in reqs),
                   "ttft_avg": round(statistics.mean(ttfts), 2) if ttfts else None}
            with open(HERE / "results.jsonl", "a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"{a.name} {task} #{run}: {graded['passed']}/{graded['total']} in {row['wall']}s, "
                  f"{row['requests']} req, {row['completion_tokens']} out-tok, failed={graded['failed']}", flush=True)
finally:
    proxy.terminate()
