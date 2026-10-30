#!/usr/bin/env python3
"""exam-prep preview: check a rendered PDF's layout with as few image tokens as possible.

Overview (default): every page as a small thumbnail, up to 12 per contact sheet.
    python preview.py out/線代_題型解題卡.pdf                 -> preview/<name>-overview-1.png …
Zoom: one page at readable resolution, to inspect a problem spotted in the overview.
    python preview.py out/線代_題型解題卡.pdf --page 5         -> preview/<name>-p5.png

Look at the overview first (layout, empty pages, overflowing maps, split cards); zoom only into pages that
look wrong. Thumbnails are too small to proofread text — proofread the Markdown, not the picture.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SHEET_MAX = 1568
# bold fonts for page labels: Linux, Windows, macOS
LABEL_FONTS = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]


def font(size=20):
    for p in LABEL_FONTS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def pages_of(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                         check=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))


def render(pdf: Path, first: int, last: int, dpi: int, work: Path) -> list[Image.Image]:
    subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(first), "-l", str(last), "-png", str(pdf), str(work / "p")],
                   check=True, capture_output=True)
    files = sorted(work.glob("p-*.png"), key=lambda f: int(f.stem.split("-")[-1]))
    return [Image.open(f).convert("RGB") for f in files]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", type=Path, default=Path("preview"))
    ap.add_argument("--page", type=int, help="zoom into one page instead of the overview")
    ap.add_argument("--per-sheet", type=int, default=12)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # file names may hold characters cp950 lacks
    a.out.mkdir(parents=True, exist_ok=True)
    name = a.pdf.stem
    n = pages_of(a.pdf)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        if a.page:
            if not 1 <= a.page <= n:
                sys.exit(f"page must be 1..{n}")
            im = render(a.pdf, a.page, a.page, 110, work)[0]
            s = min(1.0, SHEET_MAX / max(im.size))
            im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
            p = a.out / f"{name}-p{a.page}.png"
            im.save(p, optimize=True)
            print(p)
            return 0

        ims = render(a.pdf, 1, n, 40, work)
        cols = 6 if a.per_sheet > 8 else 4
        f = font()
        for k in range(0, n, a.per_sheet):
            chunk = ims[k:k + a.per_sheet]
            cw = (SHEET_MAX - 8 * (cols + 1)) // cols
            cells = [im.resize((cw, int(im.height * cw / im.width)), Image.LANCZOS) for im in chunk]
            ch = max(c.height for c in cells)
            rows = (len(cells) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * cw + 8 * (cols + 1), rows * (ch + 30) + 8), "#9aa0a6")
            d = ImageDraw.Draw(sheet)
            for i, c in enumerate(cells):
                x, y = 8 + (i % cols) * (cw + 8), 8 + (i // cols) * (ch + 30)
                d.text((x, y), f"{k + i + 1}/{n}", fill="white", font=f)
                sheet.paste(c, (x, y + 26))
            p = a.out / f"{name}-overview-{k // a.per_sheet + 1}.png"
            sheet.save(p, optimize=True)
            print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
