#!/usr/bin/env python3
"""exam-prep setup: check or install everything the scripts need.

    python setup.py --check    report what is missing; installs nothing and works offline
    python setup.py            install what is missing (needs network)

Agents with a sandbox that blocks network or writes outside the project folder (e.g. Codex's default
`workspace-write` mode) cannot install on the fly: npm packages go to ~/.exam-prep-deps and Chromium to
Playwright's browser cache. Run the install once in a normal terminal, or let the agent run it with approval.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEPS_DIR = Path.home() / ".exam-prep-deps"  # same folder render.mjs installs into
NPM_PACKAGES = ["katex", "marked", "playwright", "mermaid"]
# (import name, pip name, required)
PY_PACKAGES = [("PIL", "pillow", True), ("sympy", "sympy", True), ("numpy", "numpy", True),
               ("scipy", "scipy", True), ("matplotlib", "matplotlib", True),
               ("pptx", "python-pptx", False), ("docx", "python-docx", False)]
POPPLER = ["pdftotext", "pdfinfo", "pdftoppm"]
# same default install locations ingest.py checks; LibreOffice is usually not on PATH on Windows and macOS
SOFFICE_PATHS = ["C:/Program Files/LibreOffice/program/soffice.exe", "C:/Program Files (x86)/LibreOffice/program/soffice.exe",
                 "/Applications/LibreOffice.app/Contents/MacOS/soffice"]

# resolves each package the way render.mjs does: next to the scripts, in DEPS_DIR, then NODE_PATH
NODE_CHECK = r"""
const { createRequire } = require("module"), path = require("path"), fs = require("fs");
const bases = JSON.parse(process.argv[1]);
const out = { node: process.versions.node };
for (const name of ["katex", "marked", "playwright"]) {
  for (const b of bases) for (const base of [b, path.join(b, "node_modules")]) {
    if (out[name]) continue;
    try { out[name] = createRequire(path.join(base, "noop.js")).resolve(name); } catch {}
  }
}
out.mermaid = bases.flatMap((b) => [path.join(b, "mermaid/dist/mermaid.min.js"), path.join(b, "node_modules/mermaid/dist/mermaid.min.js")])
  .find((f) => fs.existsSync(f)) || null;
if (out.playwright) {
  try { const exe = require(out.playwright).chromium.executablePath(); out.chromium = fs.existsSync(exe) ? exe : null; } catch {}
}
console.log(JSON.stringify(out));
"""


def poppler_hint() -> str:
    system = platform.system()
    if system == "Windows":
        return "scoop install poppler（或 conda install -c conda-forge poppler），裝好後確認 bin 資料夾在 PATH"
    if system == "Darwin":
        return "brew install poppler"
    return "sudo apt-get install poppler-utils（或用發行版的套件管理器）"


def node_status() -> dict | None:
    node = shutil.which("node")
    if not node:
        return None
    bases = [str(HERE), str(DEPS_DIR)] + [p for p in os.environ.get("NODE_PATH", "").split(os.pathsep) if p]
    r = subprocess.run([node, "-e", NODE_CHECK, json.dumps(bases)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return json.loads(r.stdout) if r.returncode == 0 else {}


def cjk_font_ok() -> bool | None:
    """Only checkable on Linux; Windows and macOS ship CJK fonts."""
    if platform.system() != "Linux" or not shutil.which("fc-list"):
        return None
    r = subprocess.run(["fc-list", ":lang=zh-tw", "family"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return bool(r.stdout.strip())


def check() -> tuple[list[str], list[str]]:
    """Return (report lines, names of missing required items)."""
    lines, missing = [], []

    def row(ok: bool | None, name: str, hint: str = "", required: bool = True):
        mark = "✓" if ok else ("–" if ok is None or not required else "✗")
        lines.append(f"{mark} {name}" + (f"：{hint}" if hint and ok is False else ""))
        if required and ok is False:
            missing.append(name)

    st = node_status()
    if st is None:
        row(False, "Node.js 18+", "沒有安裝 Node.js（https://nodejs.org）")
    else:
        major = int(str(st.get("node", "0")).split(".")[0] or 0)
        row(major >= 18, f"Node.js {st.get('node', '?')}", "需要 18 以上")
        for name in NPM_PACKAGES:
            row(bool(st.get(name)), f"npm：{name}", f"執行 setup.py 安裝到 {DEPS_DIR}")
        row(bool(st.get("chromium")), "Chromium（Playwright）",
            "執行 setup.py 安裝（要能連到 Playwright 的下載伺服器）；或把 PLAYWRIGHT_BROWSERS_PATH 設成已有的瀏覽器資料夾")
    for mod, pip_name, required in PY_PACKAGES:
        row(importlib.util.find_spec(mod) is not None, f"Python：{pip_name}",
            "執行 setup.py 安裝" if required else "選用，讀 PPTX／DOCX 時需要", required)
    for tool in POPPLER:
        row(shutil.which(tool) is not None, f"poppler：{tool}", poppler_hint())
    font = cjk_font_ok()
    row(font if font is not None else None, "中文字型（Noto CJK）",
        "sudo apt-get install fonts-noto-cjk；缺字型時 PDF 中文會變成方框", required=font is not None)
    soffice = shutil.which("soffice") or any(Path(p).exists() for p in SOFFICE_PATHS)
    row(bool(soffice) or None, "LibreOffice（選用）", "", required=False)
    row(shutil.which("pandoc") is not None or None, "pandoc（選用）", "", required=False)
    return lines, missing


def pip_install(pkgs: list[str]) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "-q", *pkgs]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode and "externally-managed" in (r.stdout + r.stderr):
        r = subprocess.run(cmd + ["--break-system-packages"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
    if r.returncode:
        print(r.stderr.strip()[-800:], file=sys.stderr)
    return r.returncode == 0


def install() -> None:
    st = node_status()
    npm = shutil.which("npm")
    if st is not None and npm:
        todo = [n for n in NPM_PACKAGES if not st.get(n)]
        if todo:
            print(f"安裝 npm 套件到 {DEPS_DIR}：{' '.join(todo)}")
            DEPS_DIR.mkdir(parents=True, exist_ok=True)
            subprocess.run([npm, "install", "--silent", "--prefix", str(DEPS_DIR), *todo])
            st = node_status() or {}
        if st.get("playwright") and not st.get("chromium"):
            print("安裝 Chromium（Playwright）")
            # the CLI of the playwright package we resolve, so the browser matches its version
            cli = Path(st["playwright"]).resolve().parent / "cli.js"
            subprocess.run([shutil.which("node"), str(cli), "install", "chromium"])
    todo = [pip_name for mod, pip_name, _ in PY_PACKAGES if importlib.util.find_spec(mod) is None]
    if todo:
        print(f"安裝 Python 套件：{' '.join(todo)}")
        pip_install(todo)
        importlib.invalidate_caches()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only report, install nothing")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ✓ ✗ cannot be printed in cp950

    if not a.check:
        install()
    lines, missing = check()
    print("\n".join(lines))
    if missing:
        print(f"\n缺少 {len(missing)} 項必要項目。" +
              ("執行 `python setup.py`（需要網路）安裝；poppler、Node.js、字型要照提示自行安裝。" if a.check
               else "標 ✗ 的項目仍未就緒，請照提示處理。"))
        return 1
    print("\n全部就緒。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
