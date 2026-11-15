#!/usr/bin/env python3
"""Validate every skill (skills/<name>/ and suites/<suite>/skills/<name>/) before it is published.

Checks (errors fail CI):
  - <skill>/SKILL.md exists, exactly one SKILL.md per skill (outside evals/)
  - frontmatter is valid YAML with only the keys Claude.ai accepts on upload
  - name is kebab-case, <= 64 chars, and matches the folder name
  - description is a string, <= 1024 chars, no angle brackets
  - compatibility <= 500 chars
  - metadata.version is semantic versioning (x.y.z)
  - the version has an entry in <skill>/CHANGELOG.md
  - the skill is linked from README.md and README.en.md, and covered by a plugin in
    .claude-plugin/marketplace.json (listed in its skills, or under its source directory's skills/)
  - every plugin whose source is its own directory has .claude-plugin/plugin.json with the same name,
    at least one skill under skills/, and no symlinks (claude.ai marketplace sync rejects these)
  - Python scripts compile, JS scripts pass `node --check` (when node is available)

Usage:  python tools/validate_skills.py            # all skills
        python tools/validate_skills.py exam-prep  # one skill
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_paths import ROOT, rel, skill_dirs  # noqa: E402

MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise ValueError("missing or malformed YAML frontmatter (must start and end with ---)")
    data = yaml.safe_load(m.group(1))
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data


def marketplace_plugins() -> list[dict]:
    return json.loads(MARKETPLACE.read_text(encoding="utf-8")).get("plugins", []) if MARKETPLACE.exists() else []


def plugin_dir(plugin: dict) -> Path | None:
    """The plugin's own directory, or None when it borrows the repo root ("./" with a skills list)."""
    src = plugin.get("source")
    if not isinstance(src, str) or src.rstrip("/") in (".", ""):
        return None
    return (ROOT / src).resolve()


def covered_by_marketplace(d: Path) -> bool:
    for pl in marketplace_plugins():
        if f"./{rel(d)}" in {s.rstrip("/") for s in pl.get("skills", [])}:
            return True
        pd = plugin_dir(pl)
        if pd is not None and d.resolve().parent == pd / "skills":
            return True
    return False


def check_plugins() -> list[str]:
    errs: list[str] = []
    for pl in marketplace_plugins():
        name, pd = pl.get("name", "?"), plugin_dir(pl)
        if pd is None:
            continue
        where = f"plugin {name} ({pl['source']})"
        if not pd.is_dir():
            errs.append(f"{where}: source directory not found")
            continue
        manifest = pd / ".claude-plugin" / "plugin.json"
        if not manifest.exists():
            errs.append(f"{where}: .claude-plugin/plugin.json not found")
        else:
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                if data.get("name") != name:
                    errs.append(f"{where}: plugin.json name '{data.get('name')}' does not match marketplace name")
            except json.JSONDecodeError as e:
                errs.append(f"{where}: plugin.json is not valid JSON: {e}")
        if not list(pd.glob("skills/*/SKILL.md")):
            errs.append(f"{where}: no skills/<name>/SKILL.md under the source directory")
        if "skills" in pl or "strict" in pl:
            errs.append(f"{where}: drop 'skills'/'strict'; the plugin's own skills/ folder is used")
        links = [rel(p) for p in pd.rglob("*") if p.is_symlink()]
        if links:
            errs.append(f"{where}: symlinks are not allowed in a plugin: {links}")
    return errs


def check_skill(d: Path) -> list[str]:
    errs: list[str] = []
    name = d.name
    skill_md = d / "SKILL.md"
    if not skill_md.exists():
        return [f"{name}: SKILL.md not found"]

    extra = [p for p in d.rglob("SKILL.md") if p != skill_md and "evals" not in p.relative_to(d).parts
             and "node_modules" not in p.parts and "__pycache__" not in p.parts]
    if extra:
        errs.append(f"{name}: extra SKILL.md files (Claude.ai rejects these on upload): {[str(p.relative_to(d)) for p in extra]}")

    try:
        fm = frontmatter(skill_md)
    except Exception as e:  # noqa: BLE001
        return errs + [f"{name}: {e}"]

    unexpected = set(fm) - ALLOWED_KEYS
    if unexpected:
        errs.append(f"{name}: unexpected frontmatter keys {sorted(unexpected)}; allowed: {sorted(ALLOWED_KEYS)}")

    fm_name = str(fm.get("name", "")).strip()
    if not fm_name:
        errs.append(f"{name}: missing 'name'")
    else:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm_name) or len(fm_name) > 64:
            errs.append(f"{name}: name '{fm_name}' must be kebab-case and at most 64 characters")
        if fm_name != name:
            errs.append(f"{name}: frontmatter name '{fm_name}' does not match folder name '{name}'")

    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errs.append(f"{name}: missing 'description'")
    else:
        if len(desc) > 1024:
            errs.append(f"{name}: description is {len(desc)} characters (max 1024)")
        if "<" in desc or ">" in desc:
            errs.append(f"{name}: description cannot contain < or >")

    comp = fm.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or len(comp) > 500):
        errs.append(f"{name}: compatibility must be a string of at most 500 characters")

    version = str((fm.get("metadata") or {}).get("version", ""))
    if not SEMVER.match(version):
        errs.append(f"{name}: metadata.version must be x.y.z (got '{version}')")
    else:
        changelog = d / "CHANGELOG.md"
        if not changelog.exists():
            errs.append(f"{name}: CHANGELOG.md not found")
        elif not re.search(rf"^##\s*\[?{re.escape(version)}\]?", changelog.read_text(encoding="utf-8"), re.M):
            errs.append(f"{name}: CHANGELOG.md has no '## {version}' entry")

    for readme in ("README.md", "README.en.md"):
        p = ROOT / readme
        if p.exists() and rel(d) not in p.read_text(encoding="utf-8"):
            errs.append(f"{name}: {readme} has no link to {rel(d)}/")

    if MARKETPLACE.exists() and not covered_by_marketplace(d):
        errs.append(f"{name}: not part of any plugin in .claude-plugin/marketplace.json")

    for py in d.rglob("*.py"):
        if "evals" in py.relative_to(d).parts:
            continue
        try:
            compile(py.read_text(encoding="utf-8"), str(py), "exec")
        except SyntaxError as e:
            errs.append(f"{name}: {py.relative_to(d)} does not compile: {e}")
    if shutil.which("node"):
        for js in list(d.rglob("*.mjs")) + list(d.rglob("*.js")):
            if "node_modules" in js.parts:
                continue
            r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            if r.returncode:
                errs.append(f"{name}: {js.relative_to(d)} fails node --check:\n{r.stderr.strip()}")
    return errs


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ✓ ✗ are not in cp950 (Traditional Chinese Windows)
    only = set(sys.argv[1:])
    found = skill_dirs()
    dirs = [d for d in found if not only or d.name in only]
    if not dirs:
        print("no skills found")
        return 1
    all_errs: list[str] = []
    names = [d.name for d in found]
    for dup in sorted({n for n in names if names.count(n) > 1}):
        all_errs.append(f"{dup}: more than one skill folder with this name: {[rel(d) for d in found if d.name == dup]}")
    for d in dirs:
        errs = check_skill(d)
        print(f"{'✗' if errs else '✓'} {d.name}")
        all_errs += errs
    if not only:
        plugin_errs = check_plugins()
        print(f"{'✗' if plugin_errs else '✓'} marketplace plugins")
        all_errs += plugin_errs
    if all_errs:
        print("\n" + "\n".join(f"  - {e}" for e in all_errs))
        return 1
    print(f"\nAll {len(dirs)} skill(s) valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
