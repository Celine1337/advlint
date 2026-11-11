#!/usr/bin/env python3
"""Write tests/demo: datapack advancements with one of each issue."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "tests", "demo", "data", "demo", "advancements")

DISPLAY = {
    "icon": {"item": "minecraft:diamond"},
    "title": {"text": "Getting Diamonds"},
    "description": {"text": "Mine a diamond"},
    "frame": "task",
}
CRIT = {"has_diamond": {"trigger": "minecraft:inventory_changed"}}

ROOT_ADV = {
    "display": dict(DISPLAY, background="minecraft:textures/gui/advancements/backgrounds/stone.png"),
    "criteria": CRIT,
    "requirements": [["has_diamond"]],
    "rewards": {"experience": 100},
}
CHILD = {
    "parent": "demo:root",
    "display": dict(DISPLAY, frame="epic", show_toast="yes"),
    "criteria": {"a": {"trigger": "minecraft:inventory_changed"},
                 "b": {"trigger": "minecraft:impossible"}},
    "requirements": [["a"]],
}
BROKEN = {
    "criteria": {"x": {}},
    "requirements": [["x"], ["nope"]],
    "rewards": {"experience": -5},
}
CYCLE_A = {"parent": "demo:cycle_b", "display": DISPLAY, "criteria": CRIT,
           "requirements": [["has_diamond"]]}
CYCLE_B = {"parent": "demo:cycle_a", "display": DISPLAY, "criteria": CRIT,
           "requirements": [["has_diamond"]]}


def main():
    os.makedirs(DEMO, exist_ok=True)
    for name, data in (("root", ROOT_ADV), ("child", CHILD), ("broken", BROKEN),
                       ("cycle_a", CYCLE_A), ("cycle_b", CYCLE_B)):
        with open(os.path.join(DEMO, name + ".json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    print("wrote", DEMO)


if __name__ == "__main__":
    main()