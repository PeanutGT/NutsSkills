"""Local dashboard server (stdlib only).

    python scripts/server.py [--port 8765] [--no-open]

Security model: binds 127.0.0.1 only; the Host header must be localhost; every request that
changes something (POST/PUT/PATCH/DELETE) must carry the per-start token, which is injected into
index.html. Audio and the library are read-only over GET. The dashboard never writes outside the
workspace; deleting a take or a user style moves it to the workspace trash.
"""
from __future__ import annotations

import argparse
import json
import os
import mimetypes
import re
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import gpu
import jobs
import library
import pipeline
import msconfig
import postprocess
from common import SKILL_DIR, ensure_workspace, read_json, set_dotted, unset_dotted, workspace_dir, write_json

DASH = SKILL_DIR / "dashboard"
SCRIPTS = SKILL_DIR / "scripts"
TOKEN = secrets.token_urlsafe(24)
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
MAX_BODY = 1_000_000
QUEUE = None  # jobs.JobQueue, created in get_queue()
ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
TAKE_RE = re.compile(r"^(?!\.)[\w.\-]{1,120}$")  # take ids may contain CJK from the title slug; never start with a dot


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


# --------------------------------------------------------------------------- jobs
def get_queue():
    global QUEUE
    if QUEUE is None:
        QUEUE = jobs.JobQueue(ensure_workspace())
    return QUEUE


# --------------------------------------------------------------------------- api
def api_state() -> dict:
    ws = ensure_workspace()
    cfg, _ = msconfig.load_config(ws)
    tier, info = msconfig.resolve_tier(cfg)
    styles, moods, wfs = msconfig.load_styles(ws), msconfig.load_moods(ws), msconfig.load_workflows(ws)
    return {
        "workspace": str(ws), "engine": cfg.get("engine"), "tier": tier, "gpu": info,
        "problems": msconfig.validate(ws),
        "styles": [{"id": k, **{f: v.get(f) for f in ("name", "description", "caption", "bpm", "keys", "duration", "tags", "name_zh", "description_zh")},
                    "source": v.get("_source")} for k, v in styles.items()],
        "moods": [{"id": k, "caption": v.get("caption"), "label_zh": v.get("label_zh"), "bpm_delta": v.get("bpm_delta", 0), "source": v.get("_source")}
                  for k, v in moods.items()],
        "workflows": [{"id": k, "name": v.get("name"), "description": v.get("description"),
                       "name_zh": v.get("name_zh"), "description_zh": v.get("description_zh"),
                       "defaults": v.get("defaults", {}), "stages": v.get("stages", []),
                       "steps": next((st.get("steps", []) for st in v.get("stages", []) if st.get("id") == "postprocess"), []),
                       "source": v.get("_source")} for k, v in wfs.items()],
        "qualities": list(cfg["quality"]["presets"]),
        "defaults": {"quality": cfg["quality"].get("default"), "workflow": cfg["workflow"].get("default"),
                     "duration": cfg["generation"].get("duration")},
        "tier_caps": cfg["hardware"]["tiers"].get(tier, {}),
        "worker": get_queue().list(10**12)["worker"],
    }


def _spec_from_body(body: dict) -> dict:
    ws = workspace_dir()
    cfg, _ = msconfig.load_config(ws)
    if not body.get("style"):
        raise ApiError(400, "style is required")

    def num(key, cast):
        v = body.get(key)
        return cast(v) if v not in (None, "") else None
    try:
        return msconfig.build_spec(
            cfg, msconfig.load_styles(ws), msconfig.load_moods(ws), style_id=body["style"],
            description=str(body.get("description") or "")[:2000],
            mood_ids=[str(m) for m in body.get("moods", [])], title=(body.get("title") or None),
            duration=num("duration", float), bpm=num("bpm", int), key=(body.get("key") or None),
            variants=num("variants", int), quality=(body.get("quality") or None),
            workflow=(body.get("workflow") or None), seed=num("seed", int),
            caption_extra=str(body.get("caption_extra") or "")[:1000], workflows=msconfig.load_workflows(ws),
            lexicon=msconfig.load_lexicon(ws), caption_override=(str(body.get("caption") or "")[:1000] or None))
    except KeyError as exc:
        raise ApiError(400, str(exc.args[0]))
    except (TypeError, ValueError) as exc:
        raise ApiError(400, f"bad number: {exc}")


def api_plan(body: dict) -> dict:
    """Live preview: what caption / BPM / key / warnings would this request produce? (no generation)"""
    spec = _spec_from_body(body)
    ws = workspace_dir()
    cfg, _ = msconfig.load_config(ws)
    r = msconfig.resolve_params(cfg, spec.get("quality"), {"duration": spec.get("duration"), "batch_size": spec.get("variants")})
    return {"spec": spec, "params": r["params"], "tier": r["tier"], "quality": r["quality"], "warnings": r["warnings"]}


def api_submit(body: dict) -> dict:
    """Enqueue a generation. Body: a ready spec ({"spec": {...}}) or the dashboard form fields."""
    spec = body.get("spec") if isinstance(body.get("spec"), dict) else _spec_from_body(body)
    if not spec.get("caption"):
        raise ApiError(400, "spec has no caption")
    engine = body.get("engine")
    if engine not in (None, "", "ace", "mock"):
        raise ApiError(400, "engine must be ace or mock")
    job = get_queue().submit(spec, engine or None, source=str(body.get("source") or "dashboard")[:20])
    return {"job": job["id"], "spec": spec, "position": job.get("queue_position")}


def api_jobs(url) -> dict:
    q = parse_qs(url.query)
    since = int((q.get("since") or ["0"])[0] or 0)
    if (q.get("wait") or ["0"])[0] == "1":
        get_queue().wait(since, timeout=20)
    return get_queue().list(since)


def api_job(job_id: str) -> dict:
    job = get_queue().get(job_id)
    if not job:
        raise ApiError(404, "unknown job")
    return job


def api_check() -> dict:
    """Environment report (same data as `engine.py check`) for the dashboard's setup panel."""
    proc = subprocess.run([sys.executable, str(SCRIPTS / "engine.py"), "check"], capture_output=True, text=True,
                          encoding="utf-8", cwd=str(SCRIPTS), timeout=60)
    try:
        return json.loads(proc.stdout)
    except ValueError:
        raise ApiError(500, (proc.stderr or proc.stdout or "check failed")[-400:])


def api_tracks() -> list:
    return library.list_takes()


def api_track(take_id: str) -> dict:
    take = library.get_take(take_id)
    if not take:
        raise ApiError(404, "unknown take")
    return take


def api_finalize(take_id: str, body: dict) -> dict:
    try:
        return postprocess.run_for_take(take_id, body.get("variant"), body.get("workflow") or None, body.get("steps"),
                                        body.get("name") or None, bool(body.get("preview", True)))
    except postprocess.PostError as exc:
        raise ApiError(400, str(exc))


def api_config_get() -> dict:
    ws = ensure_workspace()
    cfg, prov = msconfig.load_config(ws)
    return {"config": cfg, "sources": prov, "user": read_json(ws / "config.json", {}) or {}}


def api_config_set(body: dict) -> dict:
    ws = ensure_workspace()
    path = ws / "config.json"
    user = read_json(path, {}) or {}
    for key, value in (body.get("set") or {}).items():
        set_dotted(user, str(key), value)
    for key in body.get("unset") or []:
        unset_dotted(user, str(key))
    write_json(path, user)
    return {"ok": True, "problems": msconfig.validate(ws)}


KINDS = {"styles", "moods", "workflows"}


def api_item_save(kind: str, body: dict) -> dict:
    if kind not in KINDS:
        raise ApiError(404, "unknown collection")
    if not isinstance(body, dict) or not body.get("id"):
        raise ApiError(400, "item needs an id")
    if not ID_RE.match(str(body["id"])):
        raise ApiError(400, "id may only contain letters, digits, - _ .")
    path = msconfig.save_user_item(kind, body)
    return {"ok": True, "file": str(path)}


def api_item_delete(kind: str, item_id: str) -> dict:
    if kind not in KINDS or not ID_RE.match(item_id):
        raise ApiError(404, "unknown item")
    return {"ok": msconfig.delete_user_item(kind, item_id)}


# --------------------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    server_version = "MusicStudio/1"

    def log_message(self, fmt, *args):  # quiet
        pass

    # -- helpers
    def _json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self) -> bool:
        raw = self.headers.get("Host") or ""
        host = raw[:raw.index("]") + 1] if raw.startswith("[") else raw.split(":")[0]
        return host in ALLOWED_HOSTS

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ApiError(413, "body too large")
        if not n:
            return {}
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            raise ApiError(400, "invalid JSON")
        return data

    def _dispatch(self, method: str):
        try:
            if not self._host_ok():
                raise ApiError(403, "bad host")
            url = urlparse(self.path)
            path = url.path
            if method != "GET" and self.headers.get("X-Token") != TOKEN:
                raise ApiError(403, "missing or wrong token")
            if path.startswith("/api/"):
                return self._json(self._route(method, [unquote(x) for x in path[5:].strip("/").split("/")], url))
            if method == "GET":
                return self._static(path, url)
            raise ApiError(404, "not found")
        except ApiError as exc:
            self._json({"error": exc.message}, exc.status)
        except Exception as exc:  # noqa: BLE001
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    def do_GET(self): self._dispatch("GET")
    def do_POST(self): self._dispatch("POST")
    def do_PUT(self): self._dispatch("PUT")
    def do_PATCH(self): self._dispatch("PATCH")
    def do_DELETE(self): self._dispatch("DELETE")

    # -- routing
    def _route(self, method, p, url):
        n = len(p)
        if p == ["state"] and method == "GET":
            return api_state()
        if p == ["plan"] and method == "POST":
            return api_plan(self._body())
        if p == ["check"] and method == "GET":
            return api_check()
        if p in (["jobs"], ["generate"]) and method == "POST":
            return api_submit(self._body())
        if p == ["jobs"] and method == "GET":
            return api_jobs(url)
        if n == 2 and p[0] == "jobs" and method == "GET":
            return api_job(p[1])
        if n == 3 and p[0] == "jobs" and p[2] == "cancel" and method == "POST":
            try:
                return get_queue().cancel(p[1])
            except KeyError:
                raise ApiError(404, "unknown job")
        if p == ["worker"] and method == "GET":
            return get_queue().list(10**12)["worker"]
        if p == ["worker", "unload"] and method == "POST":
            get_queue().unload()
            return {"ok": True}
        if p == ["tracks"] and method == "GET":
            return api_tracks()
        if n == 2 and p[0] == "tracks":
            if not TAKE_RE.match(p[1]):
                raise ApiError(404, "unknown take")
            if method == "GET":
                return api_track(p[1])
            if method == "PATCH":
                try:
                    return library.annotate(p[1], self._body())
                except KeyError as exc:
                    raise ApiError(404, str(exc.args[0]))
                except (ValueError, TypeError) as exc:
                    raise ApiError(400, str(exc))
            if method == "DELETE":
                return {"ok": library.trash_take(p[1])}
        if n == 3 and p[0] == "tracks" and p[2] == "finalize" and method == "POST":
            return api_finalize(p[1], self._body())
        if p == ["config"]:
            if method == "GET":
                return api_config_get()
            if method == "PUT":
                return api_config_set(self._body())
        if n == 2 and p[0] in KINDS and method == "PUT":
            body = self._body()
            body["id"] = p[1]
            return api_item_save(p[0], body)
        if n == 2 and p[0] in KINDS and method == "DELETE":
            return api_item_delete(p[0], p[1])
        raise ApiError(404, "no such endpoint")

    # -- static + audio
    def _static(self, path: str, url):
        if path.startswith("/audio/"):
            parts = unquote(path[len("/audio/"):]).split("/", 1)
            if len(parts) != 2 or not TAKE_RE.match(parts[0]):
                raise ApiError(404, "not found")
            f = library.resolve_file(parts[0], parts[1])
            if f is None or not f.is_file():
                raise ApiError(404, "not found")
            return self._send_file(f, attachment=("download" in parse_qs(url.query)))
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        if name not in ("index.html", "app.js", "style.css"):
            raise ApiError(404, "not found")
        f = DASH / name
        if name == "index.html":
            html = f.read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)
            return
        self._send_file(f, cache=False)

    def _send_file(self, f: Path, attachment=False, cache=True):
        size = f.stat().st_size
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if f.suffix == ".flac":
            ctype = "audio/flac"
        start, end, status = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                else:
                    start = max(0, size - int(m.group(2)))
                end = min(end, size - 1)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                status = 206
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{f.name}"')
        self.send_header("Cache-Control", "no-store" if not cache else "private, max-age=60")
        self.end_headers()
        try:
            with open(f, "rb") as fh:
                fh.seek(start)
                left = length
                while left > 0:
                    chunk = fh.read(min(65536, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("refusing to bind to a non-local address")
    return ThreadingHTTPServer((host, port), Handler)


def running_server(ws: Path) -> dict | None:
    """The server.json of a live server for this workspace, or None."""
    info = read_json(ws / "server.json")
    if not info:
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(info["url"] + "api/worker", timeout=2) as r:
            if r.status == 200:
                return info
    except Exception:  # noqa: BLE001
        pass
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args(argv)
    ws = ensure_workspace()
    cfg, _ = msconfig.load_config(ws)
    live = running_server(ws)
    if live:
        print(json.dumps({"event": "already_running", "url": live["url"], "workspace": str(ws)}), flush=True)
        if not args.no_open:
            webbrowser.open(live["url"])
        return 0
    port = args.port or int(cfg.get("dashboard", {}).get("port", 8765))
    host = cfg.get("dashboard", {}).get("host", "127.0.0.1")
    try:
        srv = make_server(host, port)
    except OSError:
        srv = make_server(host, 0)  # configured port busy (another app): take any free one
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    moved = pipeline.sweep_orphans(ws)
    get_queue()
    # msclient.py (Claude's side) finds the server and its write token here. Same user, same machine, localhost only.
    write_json(ws / "server.json", {"url": url, "port": srv.server_address[1], "token": TOKEN, "pid": os.getpid(),
                                    "started": time.strftime("%Y-%m-%dT%H:%M:%S")})
    print(json.dumps({"event": "listening", "url": url, "workspace": str(ws), "moved_orphans": moved}), flush=True)
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        get_queue().shutdown()
        try:
            info = read_json(ws / "server.json") or {}
            if info.get("pid") == os.getpid():
                (ws / "server.json").unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
