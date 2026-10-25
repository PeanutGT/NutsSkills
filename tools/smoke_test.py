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
                            "--theme", theme, "--html", str(html)], capture_output=True, text=True)
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
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
