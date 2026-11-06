#!/usr/bin/env python3
"""Resolve what a release name refers to: one skill, or a suite of skills.

A skill is a folder skills/<name>/; it releases at the metadata.version in its SKILL.md,
with notes from skills/<name>/CHANGELOG.md.
A suite is a plugin in .claude-plugin/marketplace.json that lists several skills; it releases
every listed skill at the newest version in suites/<name>/CHANGELOG.md, with notes from there.

Usage:  python tools/release_target.py exam-prep                     -> JSON: kind, name, version, skills
        python tools/release_target.py nuts-engineering --notes 1.1.0  -> release notes for that version
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_zip import version_of  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HEADING = re.compile(r"^##\s*\[?(\d+\.\d+\.\d+)\]?", re.M)


def suite_skills(name: str) -> list[str] | None:
    data = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    for plugin in data.get("plugins", []):
        if plugin.get("name") == name and len(plugin.get("skills", [])) > 1:
            return [Path(s.rstrip("/")).name for s in plugin["skills"]]
    return None


def resolve(name: str) -> dict:
    skill = ROOT / "skills" / name
    if (skill / "SKILL.md").exists():
        return {"kind": "skill", "name": name, "version": version_of(skill), "skills": [name],
                "changelog": f"skills/{name}/CHANGELOG.md"}
    members = suite_skills(name)
    if members is None:
        sys.exit(f"'{name}' is neither a folder under skills/ nor a suite in .claude-plugin/marketplace.json")
    changelog = ROOT / "suites" / name / "CHANGELOG.md"
    if not changelog.exists():
        sys.exit(f"suite '{name}' needs suites/{name}/CHANGELOG.md with a '## <version>' entry")
    m = HEADING.search(changelog.read_text(encoding="utf-8"))
    if not m:
        sys.exit(f"suites/{name}/CHANGELOG.md has no '## <version>' entry")
    return {"kind": "suite", "name": name, "version": m.group(1), "skills": members,
            "changelog": f"suites/{name}/CHANGELOG.md"}


def notes(target: dict, version: str) -> str:
    text = (ROOT / target["changelog"]).read_text(encoding="utf-8")
    m = re.search(rf"^##\s*\[?{re.escape(version)}\]?.*?\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    body = m.group(1).strip() if m else ""
    readme = "詳見 [README](https://github.com/PeanutGT/NutsSkills#安裝)。"
    if target["kind"] == "skill":
        install = (f"**安裝 Install**：下載下方的 `{target['name']}-{version}.zip`，到 Claude.ai 的 Customize → Skills → ＋ → "
                   f"Upload a skill 上傳（不用解壓縮）。 Claude Code：`/plugin marketplace add PeanutGT/NutsSkills`。{readme}")
    else:
        install = (f"**安裝 Install**：Claude Code：`/plugin marketplace add PeanutGT/NutsSkills`，再 "
                   f"`/plugin install {target['name']}@nutsskills`（一次裝好全部 {len(target['skills'])} 個 skill）。"
                   f" Claude.ai：下方每個 zip 是一個 skill，到 Customize → Skills → ＋ → Upload a skill 逐一上傳，"
                   f"建議先上傳 `{target['skills'][0]}`。{readme}")
    return f"{body}\n\n---\n{install}\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--notes", metavar="VERSION", help="print release notes for VERSION instead of the JSON")
    a = ap.parse_args()
    target = resolve(a.name)
    print(notes(target, a.notes) if a.notes else json.dumps(target, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
