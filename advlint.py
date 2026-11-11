#!/usr/bin/env python3
"""advlint - validator for Minecraft datapack advancement JSON files.

Checks criteria and triggers, requirements wiring, parent links and cycles,
display fields and rewards. Single file, standard library only, Python 3.9+.
"""

import argparse
import json
import os
import re
import sys

__version__ = "1.0.0"

ERROR = "error"
WARN = "warning"

ID_RE = re.compile(r"^(?:[a-z0-9_.-]+:)?[a-z0-9_./-]+$")
FRAMES = {"task", "goal", "challenge"}

KNOWN_TRIGGERS = {
    "minecraft:inventory_changed", "minecraft:player_killed_entity",
    "minecraft:entity_killed_player", "minecraft:impossible", "minecraft:location",
    "minecraft:enter_block", "minecraft:item_used_on_block", "minecraft:consume_item",
    "minecraft:effects_changed", "minecraft:used_totem", "minecraft:nether_travel",
    "minecraft:placed_block", "minecraft:player_hurt_entity",
    "minecraft:player_interacted_with_entity", "minecraft:recipe_unlocked",
    "minecraft:slept_in_bed", "minecraft:summoned_entity", "minecraft:tame_animal",
    "minecraft:target_hit", "minecraft:tick", "minecraft:used_ender_eye",
    "minecraft:villager_trade", "minecraft:brewed_potion", "minecraft:construct_beacon",
    "minecraft:enchanted_item", "minecraft:fishing_rod_hooked",
    "minecraft:hero_of_the_village", "minecraft:levitation", "minecraft:shot_crossbow",
    "minecraft:killed_by_crossbow", "minecraft:channeled_lightning",
    "minecraft:bee_nest_destroyed", "minecraft:cured_zombie_villager",
    "minecraft:filled_bucket", "minecraft:slide_down_block",
    "minecraft:thrown_item_picked_up_by_entity", "minecraft:player_sheared_equipment",
    "minecraft:avoid_vibration", "minecraft:allay_drop_item_on_block",
    "minecraft:kill_mob_near_sculk_catalyst", "minecraft:any_block_use",
    "minecraft:default_block_use", "minecraft:crafter_recipe_crafted",
    "minecraft:fall_after_explosion", "minecraft:spear_mobs",
}


class Issue:
    __slots__ = ("code", "severity", "file", "line", "message")

    def __init__(self, code, severity, file, line, message):
        self.code = code
        self.severity = severity
        self.file = file
        self.line = line
        self.message = message

    def as_dict(self):
        return {"code": self.code, "severity": self.severity, "file": self.file,
                "line": self.line, "message": self.message}


def valid_id(s):
    return isinstance(s, str) and bool(s) and bool(ID_RE.match(s))


def text_ok(v):
    return isinstance(v, (str, dict, list))


def check_display(display, has_parent, add):
    if not isinstance(display, dict):
        add("A009", ERROR, "'display' must be an object")
        return
    for field in ("title", "description"):
        if field not in display:
            add("A009", ERROR, "display missing '%s'" % field)
        elif not text_ok(display[field]):
            add("A009", ERROR, "display '%s' must be text or a component" % field)
    if "icon" not in display:
        add("A009", ERROR, "display missing 'icon'")
    else:
        icon = display["icon"]
        if not isinstance(icon, dict) or not valid_id(icon.get("item", icon.get("id"))):
            add("A011", ERROR, "display icon needs a valid 'item' id")
    frame = display.get("frame")
    if frame is not None and frame not in FRAMES:
        add("A010", ERROR, "display frame must be task/goal/challenge (got %r)" % frame)
    for b in ("show_toast", "announce_to_chat", "hidden"):
        v = display.get(b)
        if v is not None and not isinstance(v, bool):
            add("A012", ERROR, "display '%s' must be a boolean" % b)
    if not has_parent and not display.get("background"):
        add("A017", ERROR, "root advancement with display needs a 'background'")


def check_rewards(rewards, add):
    if not isinstance(rewards, dict):
        add("A013", ERROR, "'rewards' must be an object")
        return
    exp = rewards.get("experience")
    if exp is not None and (not isinstance(exp, int) or isinstance(exp, bool) or exp < 0):
        add("A013", ERROR, "rewards experience must be an integer >= 0 (got %r)" % exp)
    for key in ("loot", "recipes"):
        v = rewards.get(key)
        if v is not None and (not isinstance(v, list) or not all(valid_id(x) for x in v)):
            add("A014", ERROR, "rewards '%s' must be a list of valid ids" % key)
    fn = rewards.get("function")
    if fn is not None and not valid_id(fn):
        add("A015", ERROR, "rewards 'function' must be a valid id")


def validate(data, path, issues, stats):
    def add(code, sev, msg, line=1):
        issues.append(Issue(code, sev, path, line, msg))

    if not isinstance(data, dict):
        add("A000", ERROR, "advancement must be a JSON object")
        return
    crit = data.get("criteria")
    names = set()
    if crit is None:
        add("A001", ERROR, "missing 'criteria'")
    elif not isinstance(crit, dict) or not crit:
        add("A001", ERROR, "criteria must be a non-empty object")
    else:
        for name, c in crit.items():
            names.add(name)
            stats["criteria"] += 1
            if not isinstance(c, dict) or not c.get("trigger"):
                add("A002", ERROR, "criterion '%s' must be an object with 'trigger'" % name)
                continue
            if c["trigger"] not in KNOWN_TRIGGERS:
                add("A003", WARN, "unknown trigger '%s'" % c["trigger"])

    req = data.get("requirements")
    used = set()
    if req is not None:
        if not isinstance(req, list):
            add("A005", ERROR, "'requirements' must be a list of lists")
        else:
            for group in req:
                if not isinstance(group, list) or not all(isinstance(x, str) for x in group):
                    add("A005", ERROR, "each requirements group must be a list of criterion names")
                    continue
                for x in group:
                    used.add(x)
                    if x not in names:
                        add("A004", ERROR, "requirements references unknown criterion '%s'" % x)
        for n in sorted(names - used):
            add("A006", WARN, "criterion '%s' is not used in requirements" % n)

    parent = data.get("parent")
    if parent is not None and not valid_id(parent):
        add("A007", ERROR, "invalid parent id '%s'" % parent)

    display = data.get("display")
    if display is None:
        add("A016", WARN, "no 'display' set")
    else:
        check_display(display, parent is not None, add)

    if data.get("rewards") is not None:
        check_rewards(data["rewards"], add)


def adv_id(rel):
    parts = os.path.normpath(rel).replace("\\", "/").split("/")
    if "data" not in parts:
        return None
    i = parts.index("data")
    if i + 1 >= len(parts):
        return None
    ns = parts[i + 1]
    marker = None
    for m in ("advancements", "advancement"):
        if m in parts:
            marker = parts.index(m)
            break
    if marker is None:
        return None
    rest = parts[marker + 1:]
    if not rest:
        return None
    if rest[-1].endswith(".json"):
        rest[-1] = rest[-1][:-5]
    return ns + ":" + "/".join(rest)


def find_cycles(parents):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in parents}
    cycles = []
    stack = []

    def visit(n):
        color[n] = GRAY
        stack.append(n)
        p = parents.get(n)
        if p in color:
            if color[p] == GRAY:
                cycles.append(stack[stack.index(p):] + [p])
            elif color[p] == WHITE:
                visit(p)
        color[n] = BLACK
        stack.pop()

    for n in parents:
        if color[n] == WHITE:
            visit(n)
    return cycles


def collect(root):
    if os.path.isfile(root):
        return [root]
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build", "node_modules")]
        parts = os.path.normpath(dirpath).replace("\\", "/").split("/")
        if "advancements" in parts or "advancement" in parts:
            for fn in sorted(filenames):
                if fn.endswith(".json"):
                    found.append(os.path.join(dirpath, fn))
    return found


def audit(root):
    issues = []
    stats = {"files": 0, "advancements": 0, "criteria": 0}
    parents = {}
    idrel = {}
    isdir = os.path.isdir(root)
    for path in collect(root):
        rel = os.path.relpath(path, root) if isdir else os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            issues.append(Issue("A000", ERROR, rel, 1, "cannot read: %s" % exc))
            continue
        stats["files"] += 1
        stats["advancements"] += 1
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            issues.append(Issue("A000", ERROR, rel, exc.lineno, "invalid JSON: %s" % exc.msg))
            continue
        validate(data, rel, issues, stats)
        if isdir and isinstance(data, dict):
            aid = adv_id(rel)
            if aid:
                idrel[aid] = rel
                p = data.get("parent")
                if isinstance(p, str):
                    parents[aid] = p
    if isdir:
        for cyc in find_cycles(parents):
            first = cyc[0]
            issues.append(Issue("A008", ERROR, idrel.get(first, first), 1,
                                "parent cycle: %s" % " -> ".join(cyc)))
    return stats, issues


def colorize(text, color, enabled):
    if not enabled:
        return text
    codes = {"red": "31", "green": "32", "yellow": "33", "bold": "1"}
    return "\x1b[%sm%s\x1b[0m" % (codes[color], text)


def report(stats, issues, color, as_json):
    errors = [i for i in issues if i.severity == ERROR]
    warns = [i for i in issues if i.severity == WARN]
    if as_json:
        return json.dumps({"summary": stats, "errors": len(errors), "warnings": len(warns),
                           "issues": [i.as_dict() for i in issues]}, indent=2)
    lines = [colorize("SUMMARY", "bold", color)]
    lines.append("  advancements  %d" % stats["advancements"])
    lines.append("  criteria      %d" % stats["criteria"])
    if not issues:
        lines.append(colorize("clean: no issues found", "green", color))
        return "\n".join(lines)
    if errors:
        lines.append(colorize("ERRORS (%d)" % len(errors), "red", color))
        for i in errors:
            lines.append("  %s:%d: [%s] %s" % (i.file, i.line, i.code, i.message))
    if warns:
        lines.append(colorize("WARNINGS (%d)" % len(warns), "yellow", color))
        for i in warns:
            lines.append("  %s:%d: [%s] %s" % (i.file, i.line, i.code, i.message))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="advlint", description="Validator for Minecraft datapack advancement JSON files.")
    parser.add_argument("path", help="an advancement .json file, or a datapack directory")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--version", action="version", version="advlint " + __version__)
    opts = parser.parse_args(argv)
    if not os.path.exists(opts.path):
        sys.stderr.write("advlint: path not found: %s\n" % opts.path)
        return 2
    color = not opts.no_color and not os.environ.get("NO_COLOR") and sys.stdout.isatty()
    stats, issues = audit(opts.path)
    print(report(stats, issues, color, opts.json))
    errors = sum(1 for i in issues if i.severity == ERROR)
    warns = sum(1 for i in issues if i.severity == WARN)
    return 1 if (errors or (opts.strict and warns)) else 0


if __name__ == "__main__":
    sys.exit(main())