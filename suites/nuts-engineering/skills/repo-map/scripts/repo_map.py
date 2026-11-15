#!/usr/bin/env python3
"""Build a compact map of a repository: files, public symbols with signatures, and who imports whom.

Reading the map first lets an agent open only the files it needs instead of grepping and reading
the whole tree. Stdlib only; Python is parsed with ast, other languages with line-based patterns.

Usage:  python repo_map.py [ROOT]                 -> writes ROOT/.nuts/repo-map.md
        python repo_map.py [ROOT] --stdout        -> prints the map
        python repo_map.py [ROOT] --find NAME     -> where NAME is defined and which files use it
"""
from __future__ import annotations

import argparse
import ast
import os
import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {".git", ".hg", ".svn", ".nuts", "node_modules", "__pycache__", ".venv", "venv", "env",
             "dist", "build", "out", "target", "vendor", ".next", ".nuxt", ".tox", ".mypy_cache",
             ".pytest_cache", "coverage", ".idea", ".vscode"}
JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
LANG_EXT = {".py", ".go", ".rs", ".java", ".kt", ".cs", ".rb", ".php", ".swift", *JS_EXT}
MAX_SYMBOLS = 40

# (pattern, group holding the symbol name); the symbol text is the matched line up to "{" or "=>".
JS_PATTERNS = [
    re.compile(r"^export\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)\s*(?:<[^>]*>)?\([^)]*\)(?:\s*:\s*[^{]+)?"),
    re.compile(r"^(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)"),
    re.compile(r"^export\s+(?:const|let|var)\s+(\w+)"),
    re.compile(r"^export\s+(?:declare\s+)?(?:interface|type|enum)\s+(\w+)"),
    re.compile(r"^(?:async\s+)?function\s*\*?\s*(\w+)\s*\([^)]*\)"),
]
JS_IMPORT = re.compile(r"""(?:from\s+|import\s*\(?\s*|require\(\s*)['"]([^'"]+)['"]""")
OTHER_PATTERNS = {
    ".go": [re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(.*?(?=\s*\{|$)"),
            re.compile(r"^type\s+(\w+)\s+(?:struct|interface)\b")],
    ".rs": [re.compile(r"^\s*pub(?:\([^)]*\))?\s+(?:async\s+)?fn\s+(\w+)[^{;]*"),
            re.compile(r"^\s*pub(?:\([^)]*\))?\s+(?:struct|enum|trait)\s+(\w+)")],
    ".java": [re.compile(r"^\s*public\s+(?:\w+\s+)*(?:class|interface|enum|record)\s+(\w+)"),
              re.compile(r"^\s*public\s+(?:static\s+|final\s+|abstract\s+|synchronized\s+)*[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)")],
    ".kt": [re.compile(r"^\s*(?:data\s+|sealed\s+|abstract\s+|open\s+)*(?:class|interface|object)\s+(\w+)"),
            re.compile(r"^\s*(?:suspend\s+)?fun\s+(?:<[^>]*>\s*)?(\w+)\s*\([^)]*\)[^{=]*")],
    ".cs": [re.compile(r"^\s*public\s+(?:\w+\s+)*(?:class|interface|enum|struct|record)\s+(\w+)"),
            re.compile(r"^\s*public\s+(?:static\s+|async\s+|virtual\s+|override\s+)*[\w<>\[\],?\s]+\s+(\w+)\s*\([^)]*\)")],
    ".rb": [re.compile(r"^\s*(?:class|module)\s+([\w:]+)"), re.compile(r"^\s*def\s+([\w.?!]+)[^\n]*")],
    ".php": [re.compile(r"^\s*(?:abstract\s+|final\s+)?(?:class|interface|trait)\s+(\w+)"),
             re.compile(r"^\s*(?:public\s+)?(?:static\s+)?function\s+(\w+)\s*\([^)]*\)")],
    ".swift": [re.compile(r"^\s*(?:public\s+|open\s+)?(?:final\s+)?(?:class|struct|protocol|enum)\s+(\w+)"),
               re.compile(r"^\s*(?:public\s+|open\s+)?(?:static\s+)?func\s+(\w+)\s*\([^)]*\)[^{]*")],
}


@dataclass
class Symbol:
    name: str
    text: str
    line: int


@dataclass
class FileInfo:
    rel: str
    lines: int
    symbols: list[Symbol] = field(default_factory=list)
    raw_imports: list[str] = field(default_factory=list)
    imports: set[str] = field(default_factory=set)
    used_by: set[str] = field(default_factory=set)


def is_public(name: str) -> bool:
    return not name.startswith("_") or name == "__init__"


# ---------- file discovery ----------

def list_files(root: Path) -> list[str]:
    rels: list[str] = []
    if (root / ".git").exists():
        r = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            rels = r.stdout.splitlines()
    if not rels:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info"))
            for f in filenames:
                rels.append(Path(dirpath, f).relative_to(root).as_posix())
    return sorted(r for r in rels
                  if Path(r).suffix in LANG_EXT and not SKIP_DIRS & set(r.split("/")[:-1]))


# ---------- extraction ----------

def python_symbols(text: str, rel: str) -> tuple[list[Symbol], list[str]]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        syms = [Symbol(m.group(2), m.group(0).strip().rstrip(":"), text.count("\n", 0, m.start()) + 1)
                for m in re.finditer(r"^(class|def)\s+(\w+).*$", text, re.M) if is_public(m.group(2))]
        return syms, []

    def sig(node) -> str:
        kind = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        return f"{kind} {node.name}({ast.unparse(node.args)}){ret}"

    syms: list[Symbol] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and is_public(node.name):
            bases = ", ".join(ast.unparse(b) for b in node.bases)
            syms.append(Symbol(node.name, f"class {node.name}" + (f"({bases})" if bases else ""), node.lineno))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_public(sub.name):
                    prefix = "  .async " if isinstance(sub, ast.AsyncFunctionDef) else "  ."
                    syms.append(Symbol(sub.name, prefix + sig(sub).split("def ", 1)[1], sub.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_public(node.name):
            syms.append(Symbol(node.name, sig(node), node.lineno))

    package = rel.rsplit("/", 1)[0].replace("/", ".") if "/" in rel else ""
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".") if package else []
                parts = parts[:len(parts) - (node.level - 1)] if node.level > 1 else parts
                base = ".".join(p for p in [*parts, base] if p)
            imports.append(base)
            imports += [f"{base}.{a.name}" if base else a.name for a in node.names]
    return syms, imports


def pattern_symbols(text: str, patterns) -> list[Symbol]:
    syms: list[Symbol] = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat in patterns:
            m = pat.match(line)
            if m and is_public(m.group(1)):
                body = re.split(r"\s*(?:\{|=>)\s*", m.group(0), maxsplit=1)[0].strip().rstrip(";")
                syms.append(Symbol(m.group(1), body, i))
                break
    return syms


def extract(root: Path, rel: str) -> FileInfo:
    text = (root / rel).read_text(encoding="utf-8", errors="replace")
    info = FileInfo(rel, text.count("\n") + (0 if text.endswith("\n") or not text else 1))
    ext = Path(rel).suffix
    if ext == ".py":
        info.symbols, info.raw_imports = python_symbols(text, rel)
    elif ext in JS_EXT:
        info.symbols = pattern_symbols(text, JS_PATTERNS)
        info.raw_imports = [s for s in JS_IMPORT.findall(text) if s.startswith(".")]
    else:
        info.symbols = pattern_symbols(text, OTHER_PATTERNS.get(ext, []))
    return info


# ---------- import resolution ----------

def python_module_index(files: dict[str, FileInfo]) -> dict[str, str]:
    index: dict[str, str] = {}
    for rel in files:
        if not rel.endswith(".py"):
            continue
        mod = rel[:-3].removesuffix("/__init__").replace("/", ".")
        index[mod] = rel
        if mod.startswith("src."):
            index.setdefault(mod[4:], rel)
    return index


def resolve_js(rel: str, spec: str, files: dict[str, FileInfo]) -> str | None:
    base = posixpath.normpath(posixpath.join(posixpath.dirname(rel), spec))
    stem = base.rsplit(".", 1)[0] if base.endswith(JS_EXT) else base
    for cand in (base, *(stem + e for e in JS_EXT), *(f"{base}/index{e}" for e in JS_EXT)):
        if cand in files:
            return cand
    return None


def link(files: dict[str, FileInfo]) -> None:
    py_index = python_module_index(files)
    for rel, info in files.items():
        # scripts run from their own folder import siblings by bare name (`import common`)
        sibling = rel.rsplit("/", 1)[0].replace("/", ".") + "." if "/" in rel else ""
        for imp in info.raw_imports:
            if rel.endswith(JS_EXT):
                target = resolve_js(rel, imp, files)
            else:
                target = py_index.get(imp) or py_index.get(sibling + imp)
            if target and target != rel:
                info.imports.add(target)
                files[target].used_by.add(rel)


def scan(root: Path) -> dict[str, FileInfo]:
    files = {rel: extract(root, rel) for rel in list_files(root)}
    link(files)
    return files


# ---------- output ----------

def build_map(root: Path, files: dict[str, FileInfo] | None = None) -> str:
    root = Path(root)
    files = files if files is not None else scan(root)
    n_syms = sum(len(f.symbols) for f in files.values())
    out = [f"# Repo map: {root.resolve().name}",
           f"{len(files)} files, {n_syms} public symbols. Read this first; open only the files you need.", ""]
    for rel, info in files.items():
        out.append(f"## {rel} ({info.lines} lines)")
        out += [f"- {s.text}" for s in info.symbols[:MAX_SYMBOLS]]
        if len(info.symbols) > MAX_SYMBOLS:
            out.append(f"- … {len(info.symbols) - MAX_SYMBOLS} more")
        if info.imports:
            out.append("imports: " + ", ".join(sorted(info.imports)))
        if info.used_by:
            out.append("used by: " + ", ".join(sorted(info.used_by)))
        out.append("")
    return "\n".join(out)


def find(root: Path, name: str) -> str:
    files = scan(Path(root))
    hits = [(info, s) for info in files.values() for s in info.symbols if s.name == name]
    if not hits:
        return f"'{name}' is not a public symbol in this repo (try grep for private or dynamic names)."
    word = re.compile(rf"\b{re.escape(name)}\b")
    out = []
    for info, s in hits:
        out.append(f"{info.rel}:{s.line}  {s.text.strip()}")
        # only importers that actually mention the name; an import alone is a false lead
        refs = []
        for rel in [info.rel, *sorted(info.used_by)]:
            text = (Path(root) / rel).read_text(encoding="utf-8", errors="replace")
            refs += [f"{rel}:{i}" for i, line in enumerate(text.splitlines(), 1)
                     if word.search(line) and not (rel == info.rel and i == s.line)]
        if refs:
            shown = refs[:MAX_SYMBOLS]
            more = f" … {len(refs) - len(shown)} more" if len(refs) > len(shown) else ""
            out.append("  referenced at: " + ", ".join(shown) + more)
    return "\n".join(out)


def source_chars(root: Path, files: dict[str, FileInfo]) -> int:
    return sum((root / rel).stat().st_size for rel in files)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Compact map of a repository for coding agents.")
    ap.add_argument("root", nargs="?", default=".", type=Path)
    ap.add_argument("--out", type=Path, help="default: ROOT/.nuts/repo-map.md")
    ap.add_argument("--stdout", action="store_true", help="print the map instead of writing a file")
    ap.add_argument("--find", metavar="NAME", help="show where NAME is defined and which files use it")
    a = ap.parse_args(argv)
    root = a.root.resolve()
    if a.find:
        print(find(root, a.find))
        return 0
    files = scan(root)
    text = build_map(root, files)
    if a.stdout:
        print(text)
        return 0
    out = a.out or root / ".nuts" / "repo-map.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    src = source_chars(root, files)
    ratio = f", {src / len(text):.1f}x smaller" if text else ""
    print(f"wrote {out}: {len(text)} chars vs {src} chars of source{ratio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
