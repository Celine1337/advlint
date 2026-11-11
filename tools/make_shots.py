#!/usr/bin/env python3
"""Regenerate docs/audit.png and docs/clean.png. Requires Pillow.

Run: python tools/make_demo.py && python tools/make_shots.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import advlint as al
import render_terminal as rt

CLEAN = {
    "display": {
        "icon": {"item": "minecraft:diamond"},
        "title": {"text": "Getting Diamonds"},
        "description": {"text": "Mine a diamond"},
        "frame": "task",
        "background": "minecraft:textures/gui/advancements/backgrounds/stone.png",
    },
    "criteria": {"has_diamond": {"trigger": "minecraft:inventory_changed"}},
    "requirements": [["has_diamond"]],
    "rewards": {"experience": 100},
}


def render(name, ansi, cmd, title):
    rt.render(rt.parse_ansi(ansi), title, cmd, os.path.join(ROOT, "docs", name + ".png"))


def main():
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    stats, issues = al.audit(os.path.join(ROOT, "tests", "demo"))
    render("audit", al.report(stats, issues, True, False),
           "python advlint.py tests/demo", "advlint — audit")
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "data", "demo", "advancements")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "root.json"), "w", encoding="utf-8") as fh:
            json.dump(CLEAN, fh)
        stats, issues = al.audit(tmp)
        render("clean", al.report(stats, issues, True, False),
               "python advlint.py datapacks/mypack", "advlint — clean")


if __name__ == "__main__":
    main()