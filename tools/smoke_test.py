#!/usr/bin/env python3
"""End-to-end render test: figures.py -> SVG, render.mjs -> PDF in every theme.

Fails if a render errors, a Mermaid diagram fails, KaTeX leaves raw source, or a PDF is empty.
Usage:  python tools/smoke_test.py [--out DIR]
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "exam-prep"


def circuit_problems(F, figs: Path) -> list[str]:
    """Draws figs/circuit.svg for sample.md, and checks that solve_circuit follows the drawing (a reversed source
    changes the answer) and that a missing wire is reported."""
    import warnings
    import schemdraw.elements as elm

    def circuit(name, *, flip=False, missing_wire=False):
        with F.schematic(str(figs / name)) as d:
            src = F.V(12).up()
            if flip:
                src.reverse()
            r1 = F.R(4, "R₁").right().label("i →", loc="bottom")
            F.R(6, "R₂", loc="bottom").down()
            if not missing_wire:
                elm.Line().left()
        return d, r1

    problems = []
    d, r1 = circuit("circuit.svg")
    if F.solve_circuit(d).i(r1) != Fraction(6, 5):
        problems.append("solve_circuit gave the wrong current")
    d, r1 = circuit("flipped.svg", flip=True)
    if F.solve_circuit(d).i(r1) != Fraction(-6, 5):
        problems.append("solve_circuit ignored a reversed source")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        d, _ = circuit("open.svg", missing_wire=True)
    if not any("open end" in str(w.message) for w in caught):
        problems.append("no open-end warning for a missing wire")
    return problems


def make_vector_pdf(path: Path):
    """Three text pages; the middle one also has a circuit drawn as vector paths."""
    import matplotlib.pyplot as plt
    import schemdraw
    import schemdraw.elements as elm
    from matplotlib.backends.backend_pdf import PdfPages
    text = ("Node-voltage method: pick a reference node, write KCL at every other essential node, "
            "solve for the node voltages, then find branch currents and powers. ") * 3
    with PdfPages(path) as pdf:
        for page in range(3):
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.1, 0.9, text, wrap=True, fontsize=11, va="top")
            if page == 1:
                ax = fig.add_axes([0.15, 0.3, 0.7, 0.4])
                ax.axis("off")
                with schemdraw.Drawing(canvas=ax, show=False) as d:
                    elm.SourceV().up().label("20 V")
                    elm.Resistor().right().label("1 Ω")
                    elm.Dot(); d.push()
                    elm.Resistor().down().label("2 Ω")
                    d.pop()
                    elm.Resistor().right().label("6 Ω")
                    elm.Dot(); d.push()
                    elm.Resistor().down().label("20 Ω")
                    d.pop()
                    elm.Line().right()
                    elm.SourceI().down().reverse().label("2 A")
                    elm.Line().left(); elm.Line().left(); elm.Ground(); elm.Line().left()
                    d.draw(show=False)
            pdf.savefig(fig)
            plt.close(fig)


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
    problems = circuit_problems(F, out / "figs")
    print(f"[circuit] {'FAIL ' + ', '.join(problems) if problems else 'ok'}")
    failed = bool(problems)
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
        if "figure missing" in log or "image not found" in log:
            problems.append("figure check")
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
    # the figure guard must flag a question that says 如圖 without a figure, and a broken image path
    (out / "nofig.md").write_text(":::q 1 | 計算題\n如圖所示電路，求 $i$。\n:::\n\n:::q 2 | 計算題\n求 $i$。\n\n![](figs/missing.svg)\n:::\n",
                                  encoding="utf-8")
    r = subprocess.run(["node", str(SKILL / "scripts" / "render.mjs"), str(out / "nofig.md"), str(out / "nofig.pdf")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = "figure missing: question 1" in r.stderr and "image not found" in r.stderr
    print(f"[figure guard] {'ok' if ok else 'FAIL'}")
    if not ok:
        print(r.stdout + r.stderr)
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
    # a page with a vector circuit diagram (full text layer, no images) must be flagged for viewing
    vec = out / "vector.pdf"
    make_vector_pdf(vec)
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "ingest.py"), str(vec), "--out", str(out / "ingest-vector")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    report = (out / "ingest-vector" / "report.md").read_text(encoding="utf-8") if r.returncode == 0 else ""
    ok = "vector.pdf p.2：有向量圖" in report and "p.1：" not in report and "p.3：" not in report
    print(f"[ingest vector figure] {'ok' if ok else 'FAIL'}")
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
