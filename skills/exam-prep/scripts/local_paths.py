"""Install locations shared by ingest.py, preview.py and setup.py (standard library only, so setup.py --check
can use it before anything is installed). Windows folders come from the environment, not a hard-coded C:."""
from __future__ import annotations

import os

_WINDIR = os.environ.get("WINDIR", "C:/Windows")
_PROGRAM_DIRS = [os.environ.get(v) or d for v, d in (("ProgramFiles", "C:/Program Files"),
                                                    ("ProgramFiles(x86)", "C:/Program Files (x86)"))]

# bold fonts for page labels: Linux, Windows, macOS
LABEL_FONTS = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               f"{_WINDIR}/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
# LibreOffice is usually not on PATH on Windows and macOS
SOFFICE_PATHS = [f"{d}/LibreOffice/program/soffice.exe" for d in _PROGRAM_DIRS] + \
                ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
