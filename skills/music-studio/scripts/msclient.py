"""Claude's front door to the Music Studio server (the same queue the dashboard uses).

    msclient.py url                          start the server if needed (no browser) and print its URL
    msclient.py generate --spec spec.json    queue a job, follow it, print the finished take   ('-' = stdin)
                [--engine mock] [--no-wait]
    msclient.py status                       queue + GPU worker state
    msclient.py wait JOB                     follow a job that is already queued/running
    msclient.py cancel JOB
    msclient.py unload                       free the GPU now (models reload on the next job)

Output: JSON lines. While following a job: {"event":"phase"|"warn", ...}; at the end
{"event":"result","ok":true,"take":ID,"dir":...,"variants":[...]} or {"event":"error",...}.
The server is started in the background on first use and keeps the models loaded between jobs.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import SKILL_DIR, emit, ensure_workspace, read_json

SERVER = SKILL_DIR / "scripts" / "server.py"


class ClientError(Exception):
    pass


def _live(info: dict | None) -> bool:
    if not info:
        return False
    try:
        with urllib.request.urlopen(info["url"] + "api/worker", timeout=2) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def ensure_server(start: bool = True) -> dict:
    ws = ensure_workspace()
    info = read_json(ws / "server.json")
    if _live(info):
        return info
    if not start:
        raise ClientError("the Music Studio server is not running")
    log = open(ws / "server.log", "a", encoding="utf-8")
    flags = 0
    if os.name == "nt":
        flags = 0x00000008 | 0x00000200 | getattr(subprocess, "CREATE_NO_WINDOW", 0)  # detached, own group, no console
    subprocess.Popen([sys.executable, str(SERVER), "--no-open"], cwd=str(SERVER.parent), stdout=log, stderr=log,
                     stdin=subprocess.DEVNULL, creationflags=flags, start_new_session=(os.name != "nt"),
                     env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    for _ in range(60):
        time.sleep(0.5)
        info = read_json(ws / "server.json")
        if _live(info):
            return info
    raise ClientError(f"the server did not start; see {ws / 'server.log'}")


def call(info: dict, path: str, method: str = "GET", body=None, timeout: float = 30):
    req = urllib.request.Request(info["url"] + "api/" + path, method=method,
                                 data=json.dumps(body).encode("utf-8") if body is not None else None,
                                 headers={"Content-Type": "application/json", "X-Token": info["token"]})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read().decode("utf-8")).get("error")
        except Exception:  # noqa: BLE001
            msg = str(exc)
        raise ClientError(msg)


def follow(info: dict, jid: str) -> int:
    last_phase, last_pct, seen_warn = None, -1.0, 0
    while True:
        job = call(info, f"jobs/{jid}")
        for w in job.get("warnings", [])[seen_warn:]:
            emit("warn", message=w)
        seen_warn = len(job.get("warnings", []))
        if job.get("queue_position"):
            if last_phase != "queued":
                emit("phase", name="queued", position=job["queue_position"])
                last_phase = "queued"
        elif job.get("phase") != last_phase or float(job.get("pct") or 0) - last_pct >= 0.15:
            emit("phase", name=job.get("phase"), pct=round(float(job.get("pct") or 0), 2), detail=job.get("detail", ""))
            last_phase, last_pct = job.get("phase"), float(job.get("pct") or 0)
        status = job.get("status")
        if status == "done":
            take = call(info, f"tracks/{job['take_id']}")
            emit("result", ok=True, job=jid, take=take["id"], dir=take["dir"], elapsed_s=job.get("elapsed_s"),
                 variants=[{"index": v["index"], "file": v["file"], "seed": v.get("seed")} for v in take["variants"]],
                 effective=job.get("effective"), warnings=job.get("warnings", []), dashboard=info["url"])
            return 0
        if status in ("failed", "cancelled"):
            err = job.get("error") or {"code": status, "message": status}
            emit("error", job=jid, status=status, **{k: err.get(k) for k in ("code", "message", "hint")},
                 log_tail=job.get("log", [])[-15:])
            return 1
        time.sleep(1.0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("url")
    g = sub.add_parser("generate")
    g.add_argument("--spec", required=True)
    g.add_argument("--engine", choices=("ace", "mock"))
    g.add_argument("--no-wait", action="store_true")
    sub.add_parser("status")
    w = sub.add_parser("wait"); w.add_argument("job")
    c = sub.add_parser("cancel"); c.add_argument("job")
    sub.add_parser("unload")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "url":
            info = ensure_server()
            emit("server", url=info["url"])
            return 0
        if args.cmd == "generate":
            spec = json.load(sys.stdin) if args.spec == "-" else json.loads(Path(args.spec).read_text(encoding="utf-8"))
            info = ensure_server()
            r = call(info, "jobs", "POST", {"spec": spec, "engine": args.engine, "source": "claude"})
            emit("queued", job=r["job"], position=r.get("position"), dashboard=info["url"])
            return 0 if args.no_wait else follow(info, r["job"])
        info = ensure_server(start=args.cmd == "status")
        if args.cmd == "status":
            print(json.dumps(call(info, "jobs"), ensure_ascii=False, indent=1))
        elif args.cmd == "wait":
            return follow(info, args.job)
        elif args.cmd == "cancel":
            emit("cancel", **call(info, f"jobs/{args.job}/cancel", "POST", {}))
        elif args.cmd == "unload":
            emit("unload", **call(info, "worker/unload", "POST", {}))
        return 0
    except ClientError as exc:
        emit("error", code="client", message=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
