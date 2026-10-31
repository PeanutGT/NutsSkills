"""Job queue + GPU worker supervisor (runs inside server.py).

One queue, one worker, one GPU: the dashboard and Claude (via msclient.py) both submit here, so two
generations can never fight over the same card. See docs/ARCHITECTURE.md.
"""
from __future__ import annotations

import json
import os
import queue
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

import msconfig
import pipeline
from common import SKILL_DIR, read_json, write_json

WORKER_SCRIPT = SKILL_DIR / "scripts" / "ace_worker.py"
KEEP_JOBS = 100
TERMINAL = ("done", "failed", "cancelled")


class Cancelled(Exception):
    pass


def find_ace_python(ace_dir: Path) -> list[str] | None:
    import shutil
    for rel in (".venv/Scripts/python.exe", ".venv/bin/python", "python_embedded/python.exe"):
        py = ace_dir / rel
        if py.exists():
            return [str(py)]
    uv = shutil.which("uv")
    return [uv, "run", "--project", str(ace_dir), "python"] if uv else None


# --------------------------------------------------------------------------- worker
class Worker:
    """Owns the long-lived ace_worker.py process."""

    def __init__(self, on_log):
        self.proc: subprocess.Popen | None = None
        self.ace_dir: str | None = None
        self.events: queue.Queue = queue.Queue()
        self.on_log = on_log
        self.status = {"state": "stopped", "models_loaded": False, "model": None,
                       "vram_total_gb": None, "vram_free_gb": None, "pid": None}
        self.last_used = time.time()
        self.lock = threading.Lock()

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, ace_dir: str) -> None:
        with self.lock:
            if self.alive() and self.ace_dir == ace_dir:
                return
            self._stop_locked()
            py = find_ace_python(Path(ace_dir))
            if not py:
                raise RuntimeError("cannot find ACE-Step's Python (.venv, python_embedded or uv). Run setup.bat.")
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.proc = subprocess.Popen(py + [str(WORKER_SCRIPT), "--serve"], cwd=ace_dir, env=env,
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1,
                                         creationflags=flags)
            self.ace_dir = ace_dir
            self.events = queue.Queue()
            self.status.update(state="starting", models_loaded=False, model=None, pid=self.proc.pid)
            proc, events = self.proc, self.events
            threading.Thread(target=self._read_stdout, args=(proc, events), daemon=True).start()
            threading.Thread(target=self._read_stderr, args=(proc,), daemon=True).start()

    def _read_stdout(self, proc, events):
        for line in proc.stdout:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("event") == "ready":
                self.status.update(state="idle", models_loaded=ev.get("models_loaded", False), model=ev.get("model"),
                                   vram_total_gb=ev.get("vram_total_gb"), vram_free_gb=ev.get("vram_free_gb"))
            events.put(ev)
        events.put({"event": "_exit", "code": proc.wait()})

    def _read_stderr(self, proc):
        for line in proc.stderr:
            self.on_log(line.rstrip())

    def send(self, req: dict) -> None:
        self.last_used = time.time()
        self.status["state"] = "busy"
        self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def kill(self) -> None:
        with self.lock:
            self._stop_locked(force=True)

    def stop(self) -> None:
        with self.lock:
            self._stop_locked()

    def _stop_locked(self, force: bool = False) -> None:
        if self.proc is None:
            return
        proc, self.proc = self.proc, None
        try:
            if not force and proc.poll() is None:
                proc.stdin.write('{"op":"quit"}\n')
                proc.stdin.flush()
                proc.wait(timeout=20)
        except Exception:  # noqa: BLE001
            pass
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                pass
        for pipe in (proc.stdin, proc.stdout, proc.stderr):
            try:
                pipe.close()
            except Exception:  # noqa: BLE001
                pass
        self.status.update(state="stopped", models_loaded=False, model=None, pid=None, vram_free_gb=None)

    def unload(self) -> None:
        if self.alive() and self.status["state"] == "idle":
            self.proc.stdin.write('{"op":"unload"}\n')
            self.proc.stdin.flush()


# --------------------------------------------------------------------------- queue
class JobQueue:
    def __init__(self, ws: Path):
        self.ws = ws
        self.path = ws / "jobs.json"
        self.lock = threading.RLock()
        self.cv = threading.Condition(self.lock)
        self.jobs: dict[str, dict] = {}
        self.order: list[str] = []
        self.seq = 0
        self.current: str | None = None
        self.worker = Worker(self._worker_log)
        self._load()
        threading.Thread(target=self._loop, daemon=True).start()
        threading.Thread(target=self._idle_loop, daemon=True).start()

    # -- persistence
    def _load(self):
        data = read_json(self.path, {}) or {}
        for j in data.get("jobs", []):
            if j.get("status") in ("queued", "running"):
                j.update(status="failed", error={"code": "interrupted",
                                                  "message": "the server stopped while this job was waiting or running"})
            self.jobs[j["id"]] = j
            self.order.append(j["id"])
        self.seq = int(data.get("seq", 0))

    def _save(self):
        keep = self.order[-KEEP_JOBS:]
        jobs = [{k: v for k, v in self.jobs[i].items() if k not in ("log", "_cancel")} for i in keep]
        write_json(self.path, {"seq": self.seq, "jobs": jobs})

    def _touch(self, job: dict, persist: bool = False):
        self.seq += 1
        job["seq"] = self.seq
        if persist:
            self._save()
        self.cv.notify_all()

    # -- public API
    def submit(self, spec: dict, engine: str | None = None, source: str = "dashboard") -> dict:
        with self.lock:
            jid = "j" + time.strftime("%m%d%H%M%S") + secrets.token_hex(2)
            job = {"id": jid, "status": "queued", "source": source, "engine": engine, "spec": spec,
                   "title": spec.get("title") or spec.get("style"), "created": time.time(),
                   "phase": "queued", "pct": 0.0, "detail": "", "warnings": [], "events": [], "log": [],
                   "error": None, "take_id": None, "effective": None}
            self.jobs[jid] = job
            self.order.append(jid)
            self._touch(job, persist=True)
            return self.public(job)

    def cancel(self, jid: str) -> dict:
        with self.lock:
            job = self.jobs.get(jid)
            if job is None:
                raise KeyError(jid)
            if job["status"] == "queued":
                job.update(status="cancelled", phase="cancelled", finished=time.time())
                self._touch(job, persist=True)
            elif job["status"] == "running":
                job["_cancel"] = True
                self._touch(job)
                if job.get("engine_used") == "ace":
                    threading.Thread(target=self.worker.kill, daemon=True).start()
            return self.public(job)

    def get(self, jid: str) -> dict | None:
        with self.lock:
            job = self.jobs.get(jid)
            return self.public(job, log=True) if job else None

    def list(self, since: int = 0) -> dict:
        with self.lock:
            items = [self.public(self.jobs[i]) for i in self.order[-50:] if self.jobs[i].get("seq", 0) > since]
            return {"seq": self.seq, "jobs": items, "worker": dict(self.worker.status), "current": self.current}

    def wait(self, since: int, timeout: float = 25.0) -> None:
        with self.cv:
            if self.seq <= since:
                self.cv.wait(timeout)

    def public(self, job: dict, log: bool = False) -> dict:
        out = {k: v for k, v in job.items() if k not in ("log", "_cancel", "spec")}
        out["spec"] = {k: job["spec"].get(k) for k in ("title", "style", "caption", "duration", "bpm", "key", "quality", "variants", "workflow")}
        out["cancelling"] = bool(job.get("_cancel"))
        position = [i for i in self.order if self.jobs[i]["status"] == "queued"]
        out["queue_position"] = position.index(job["id"]) + 1 if job["id"] in position else None
        if log:
            out["log"] = job["log"][-200:]
        return out

    def unload(self):
        self.worker.unload()

    def shutdown(self):
        self.worker.stop()

    # -- running
    def _worker_log(self, line: str):
        with self.lock:
            if self.current and self.current in self.jobs:
                lg = self.jobs[self.current]["log"]
                lg.append(line)
                del lg[:-400]

    def _event(self, job: dict, ev: dict):
        name = ev.get("event")
        with self.lock:
            if name == "phase":
                job["phase"] = ev.get("name") or job["phase"]
                job["pct"] = max(job.get("pct", 0), float(ev.get("pct") or 0))
                job["detail"] = ev.get("detail", "")
            elif name in ("warn", "retry"):
                msg = ev.get("message") or f"retrying: {ev.get('reason')} (batch {ev.get('batch_size')})"
                if msg not in job["warnings"]:
                    job["warnings"].append(msg)
                if ev.get("code") == "cpu_decode":
                    job["cpu_decode"] = True
            job["events"].append({"t": round(time.time() - job.get("started", time.time()), 1), **{k: v for k, v in ev.items() if k != "job"}})
            del job["events"][:-80]
            self._touch(job)

    def _loop(self):
        while True:
            with self.cv:
                nxt = next((i for i in self.order if self.jobs[i]["status"] == "queued"), None)
                if nxt is None:
                    self.cv.wait(5)
                    continue
                job = self.jobs[nxt]
                job.update(status="running", started=time.time(), phase="preparing")
                self.current = nxt
                self._touch(job, persist=True)
            try:
                self._run(job)
            except Exception as exc:  # noqa: BLE001 - never let the loop die
                with self.lock:
                    job.update(status="failed", error={"code": "internal", "message": f"{type(exc).__name__}: {exc}"})
            finally:
                with self.lock:
                    job["finished"] = time.time()
                    job.pop("_cancel", None)
                    self.current = None
                    self._touch(job, persist=True)

    def _run(self, job: dict):
        try:
            ctx = pipeline.prepare(job["spec"], engine=job.get("engine"), job_id=job["id"], ws=self.ws)
        except Exception as exc:  # noqa: BLE001
            job.update(status="failed", error={"code": "prepare", "message": str(exc)})
            return
        job["engine_used"] = ctx["engine"]
        for w in ctx["warnings"]:
            self._event(job, {"event": "warn", "message": w})
        try:
            if ctx["engine"] == "mock":
                def emit(event, **fields):
                    if job.get("_cancel"):
                        raise Cancelled()
                    self._event(job, {"event": event, **fields})
                result = pipeline.run_mock(ctx, emit)
            else:
                result = self._run_ace(job, ctx)
            if job.get("_cancel"):
                raise Cancelled()
            meta = pipeline.finish(ctx, result)
            with self.lock:
                job.update(status="done", phase="done", pct=1.0, take_id=meta["id"], effective=meta.get("effective"),
                           elapsed_s=meta.get("elapsed_s"))
        except Cancelled:
            pipeline.discard(ctx, "cancelled")
            with self.lock:
                job.update(status="cancelled", phase="cancelled")
        except Exception as exc:  # noqa: BLE001
            pipeline.discard(ctx, str(exc))
            err = exc.args[0] if exc.args and isinstance(exc.args[0], dict) else {"code": "failed", "message": str(exc)}
            with self.lock:
                job.update(status="failed", error=err)

    def _run_ace(self, job: dict, ctx: dict) -> dict:
        if not self.worker.alive():  # importing torch + ACE-Step takes tens of seconds before the worker can speak
            self._event(job, {"event": "phase", "name": "loading_models", "pct": 0.01,
                              "detail": "starting the ACE-Step worker (first job only)"})
        try:
            self.worker.start(ctx["ace_dir"])
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError({"code": "worker_start", "message": str(exc)})
        self.worker.send(ctx["request"])
        last_event, stall_warned = time.time(), False
        while True:
            try:
                ev = self.worker.events.get(timeout=1.0)
            except queue.Empty:
                if job.get("_cancel") and not self.worker.alive():
                    raise Cancelled()
                if not stall_warned and time.time() - last_event > 240:
                    stall_warned = True
                    self._event(job, {"event": "warn", "code": "stalled",
                                      "message": "no progress for 4 minutes. If this keeps going, cancel the job; "
                                                 "a shorter track or quality 'draft' usually gets through."})
                continue
            last_event = time.time()
            name = ev.get("event")
            if name == "_exit":
                if job.get("_cancel"):
                    raise Cancelled()
                tail = "\n".join(job["log"][-12:])
                raise RuntimeError({"code": "worker_crashed", "message": f"the ACE-Step worker stopped (exit {ev.get('code')})",
                                    "hint": tail})
            if ev.get("job") not in (None, job["id"]):
                continue
            if name == "result":
                self.worker.last_used = time.time()
                return ev
            if name == "error":
                raise RuntimeError({k: ev.get(k) for k in ("code", "message", "hint")})
            if name != "ready":
                self._event(job, ev)

    def _idle_loop(self):
        while True:
            time.sleep(15)
            try:
                cfg, _ = msconfig.load_config(self.ws)
                minutes = float(cfg.get("engine_idle_unload_minutes", 10))
            except Exception:  # noqa: BLE001
                minutes = 10.0
            if minutes > 0 and self.current is None and self.worker.alive() \
                    and time.time() - self.worker.last_used > minutes * 60:
                self.worker.stop()
