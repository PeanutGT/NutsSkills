#!/usr/bin/env python3
"""End-to-end render test: figures.py -> SVG, render.mjs -> PDF in every theme.

Fails if a render errors, a Mermaid diagram fails, KaTeX leaves raw source, or a PDF is empty.
Usage:  python tools/smoke_test.py [--out DIR]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "exam-prep"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "smoke")
    out = ap.parse_args().out
    shutil.rmtree(out, ignore_errors=True)
    (out / "figs").mkdir(parents=True)
    shutil.copy(ROOT / "tools" / "smoke" / "sample.md", out / "sample.md")

    sys.path.insert(0, str(SKILL / "scripts"))
    import figures as F
    from scipy.stats import binom
    F.pmf_bar(range(11), [binom.pmf(k, 10, .3) for k in range(11)], str(out / "figs" / "binom.svg"),
              highlight=lambda k: k <= 2, highlight_label="P(X ≤ 2)", mean=3)

    failed = False
    for theme in ("modern", "textbook", "cheatsheet"):
        pdf, html = out / f"sample-{theme}.pdf", out / f"sample-{theme}.html"
        r = subprocess.run(["node", str(SKILL / "scripts" / "render.mjs"), str(out / "sample.md"), str(pdf),
                            "--theme", theme, "--html", str(html)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        log = r.stdout + r.stderr
        problems = []
        if r.returncode:
            problems.append(f"exit code {r.returncode}")
        if "mermaid error" in log:
            problems.append("mermaid error")
        if not pdf.exists() or pdf.stat().st_size < 10_000:
            problems.append("PDF missing or too small")
        if html.exists():
            page = html.read_text(encoding="utf-8")
            if 'class="math-error"' in page or 'class="katex-error"' in page:
                problems.append("KaTeX error")
        status = "FAIL " + ", ".join(problems) if problems else f"ok ({pdf.stat().st_size // 1024} KB)"
        print(f"[{theme}] {status}")
        if problems:
            print(log)
            failed = True
    # ingest + preview on the eval inputs and the rendered PDF
    files = sorted((SKILL / "evals").glob("*/files/*"))
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "ingest.py"), *map(str, files), "--out", str(out / "ingest")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    report = out / "ingest" / "report.md"
    ok = r.returncode == 0 and report.exists() and list((out / "ingest" / "sheets").glob("*"))
    # a wrong pdftotext (e.g. xpdf from Git for Windows) "succeeds" but drops the Chinese text
    exam = out / "ingest" / "text" / "la_pastexam_2024-2025.txt"
    if ok and "線性代數" not in exam.read_text(encoding="utf-8"):
        print("[ingest] Chinese text missing from la_pastexam_2024-2025.txt")
        ok = False
    print(f"[ingest] {'ok' if ok else 'FAIL'} ({len(files)} files)")
    if not ok:
        print(r.stdout + r.stderr)
        failed = True
    # whole-book mode (threshold lowered so a 5-page PDF counts as a book) and reading a page range
    slides = next(f for f in files if f.name == "la_slides_ch5.pdf")
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "ingest.py"), str(slides), f"{slides}:2-3", "--book-pages", "2",
                        "--out", str(out / "ingest-book")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = out / "ingest-book" / "text"
    outline, part = text / "la_slides_ch5-outline.md", text / "la_slides_ch5_p2-3.txt"
    ok = (r.returncode == 0 and outline.exists() and not (text / "la_slides_ch5.txt").exists() and part.exists()
          and "p.2 ===" in part.read_text(encoding="utf-8") and "p.1 ===" not in part.read_text(encoding="utf-8"))
    print(f"[ingest book/range] {'ok' if ok else 'FAIL'}")
    if not ok:
        print(r.stdout + r.stderr)
        failed = True
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "preview.py"), str(out / "sample-modern.pdf"), "--out", str(out / "preview")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = r.returncode == 0 and list((out / "preview").glob("*-overview-*.png"))
    print(f"[preview] {'ok' if ok else 'FAIL'}")
    if not ok:
        print(r.stdout + r.stderr)
        failed = True
    # setup.py --check must see everything the steps above just used
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "setup.py"), "--check"], capture_output=True, text=True,
                       encoding="utf-8")
    print(f"[setup --check] {'ok' if r.returncode == 0 else 'FAIL'}")
    if r.returncode:
        print(r.stdout + r.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
