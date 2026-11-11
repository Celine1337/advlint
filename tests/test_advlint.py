import contextlib
import io
import json
import os
import tempfile
import unittest

import advlint as al

CLEAN = {
    "display": {
        "icon": {"item": "minecraft:diamond"},
        "title": {"text": "Getting Diamonds"},
        "description": {"text": "Mine a diamond"},
        "frame": "task",
        "background": "minecraft:textures/gui/advancements/backgrounds/stone.png",
        "show_toast": True, "announce_to_chat": True, "hidden": False,
    },
    "criteria": {"has_diamond": {"trigger": "minecraft:inventory_changed",
                                 "conditions": {"items": [{"items": ["minecraft:diamond"]}]}}},
    "requirements": [["has_diamond"]],
    "rewards": {"experience": 100},
}


def clone():
    return json.loads(json.dumps(CLEAN))


def write(root, rel, data):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def codes(issues):
    return sorted(i.code for i in issues)


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def run_src(self, data, rel="data/demo/advancements/t.json"):
        write(self.root, rel, data)
        return al.audit(self.root)

    def test_clean(self):
        _, issues = self.run_src(CLEAN)
        self.assertEqual(issues, [])

    def test_clean_child(self):
        d = clone()
        d["parent"] = "minecraft:story/mine_stone"
        del d["display"]["background"]
        _, issues = self.run_src(d)
        self.assertEqual(issues, [])

    def test_a000_not_object(self):
        path = os.path.join(self.root, "data", "demo", "advancements", "t.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("[]")
        _, issues = al.audit(self.root)
        self.assertIn("A000", codes(issues))

    def test_a001_missing_criteria(self):
        d = clone()
        del d["criteria"]
        _, issues = self.run_src(d)
        self.assertIn("A001", codes(issues))

    def test_a001_empty_criteria(self):
        d = clone()
        d["criteria"] = {}
        _, issues = self.run_src(d)
        self.assertIn("A001", codes(issues))

    def test_a002_criterion_no_trigger(self):
        d = clone()
        d["criteria"] = {"x": {}}
        d["requirements"] = [["x"]]
        _, issues = self.run_src(d)
        self.assertIn("A002", codes(issues))

    def test_a003_unknown_trigger(self):
        d = clone()
        d["criteria"]["has_diamond"]["trigger"] = "minecraft:bogus"
        _, issues = self.run_src(d)
        self.assertIn("A003", codes(issues))

    def test_a004_unknown_req(self):
        d = clone()
        d["requirements"] = [["nope"]]
        _, issues = self.run_src(d)
        self.assertIn("A004", codes(issues))

    def test_a005_req_not_list(self):
        d = clone()
        d["requirements"] = "has_diamond"
        _, issues = self.run_src(d)
        self.assertIn("A005", codes(issues))

    def test_a005_req_group_not_list(self):
        d = clone()
        d["requirements"] = ["has_diamond"]
        _, issues = self.run_src(d)
        self.assertIn("A005", codes(issues))

    def test_a006_unused_criterion(self):
        d = clone()
        d["criteria"]["extra"] = {"trigger": "minecraft:impossible"}
        _, issues = self.run_src(d)
        self.assertIn("A006", codes(issues))

    def test_a007_bad_parent(self):
        d = clone()
        d["parent"] = "Bad Parent"
        _, issues = self.run_src(d)
        self.assertIn("A007", codes(issues))

    def test_a009_display_missing_title(self):
        d = clone()
        del d["display"]["title"]
        _, issues = self.run_src(d)
        self.assertIn("A009", codes(issues))

    def test_a010_bad_frame(self):
        d = clone()
        d["display"]["frame"] = "epic"
        _, issues = self.run_src(d)
        self.assertIn("A010", codes(issues))

    def test_a011_bad_icon(self):
        d = clone()
        d["display"]["icon"] = {}
        _, issues = self.run_src(d)
        self.assertIn("A011", codes(issues))

    def test_a012_bad_bool(self):
        d = clone()
        d["display"]["show_toast"] = "yes"
        _, issues = self.run_src(d)
        self.assertIn("A012", codes(issues))

    def test_a013_bad_exp(self):
        d = clone()
        d["rewards"]["experience"] = -5
        _, issues = self.run_src(d)
        self.assertIn("A013", codes(issues))

    def test_a014_bad_loot(self):
        d = clone()
        d["rewards"]["loot"] = "not-a-list"
        _, issues = self.run_src(d)
        self.assertIn("A014", codes(issues))

    def test_a015_bad_function(self):
        d = clone()
        d["rewards"]["function"] = "Bad Fn"
        _, issues = self.run_src(d)
        self.assertIn("A015", codes(issues))

    def test_a016_no_display(self):
        d = clone()
        del d["display"]
        _, issues = self.run_src(d)
        self.assertIn("A016", codes(issues))

    def test_a017_root_no_background(self):
        d = clone()
        del d["display"]["background"]
        _, issues = self.run_src(d)
        self.assertIn("A017", codes(issues))

    def test_bad_json(self):
        path = os.path.join(self.root, "data", "demo", "advancements", "t.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("{ nope")
        _, issues = al.audit(self.root)
        self.assertIn("A000", codes(issues))

    def test_a008_cycle(self):
        a = clone()
        a["parent"] = "demo:b"
        b = clone()
        b["parent"] = "demo:a"
        write(self.root, "data/demo/advancements/a.json", a)
        write(self.root, "data/demo/advancements/b.json", b)
        _, issues = al.audit(self.root)
        self.assertIn("A008", codes(issues))

    def test_a008_self_parent(self):
        d = clone()
        d["parent"] = "demo:self"
        write(self.root, "data/demo/advancements/self.json", d)
        _, issues = al.audit(self.root)
        self.assertIn("A008", codes(issues))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return al.main(args)

    def test_exit_clean(self):
        write(self.root, "data/demo/advancements/t.json", CLEAN)
        self.assertEqual(self._run([self.root, "--no-color"]), 0)

    def test_exit_error(self):
        d = clone()
        del d["criteria"]
        write(self.root, "data/demo/advancements/t.json", d)
        self.assertEqual(self._run([self.root, "--no-color"]), 1)

    def test_exit_bad_path(self):
        self.assertEqual(self._run([os.path.join(self.root, "nope")]), 2)

    def test_strict_warning(self):
        d = clone()
        del d["display"]
        write(self.root, "data/demo/advancements/t.json", d)
        self.assertEqual(self._run([self.root, "--no-color"]), 0)
        self.assertEqual(self._run([self.root, "--no-color", "--strict"]), 1)

    def test_json(self):
        write(self.root, "data/demo/advancements/t.json", CLEAN)
        stats, issues = al.audit(self.root)
        out = json.loads(al.report(stats, issues, False, True))
        self.assertEqual(out["summary"]["advancements"], 1)
        self.assertEqual(out["summary"]["criteria"], 1)


if __name__ == "__main__":
    unittest.main()