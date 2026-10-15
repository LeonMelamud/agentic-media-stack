"""Tests for the three Instagram skills adapted from instagram-agent-skill.

English: every tool must give exactly the output upstream gave (golden files
recorded from upstream commit d03c56b before any change). Hebrew: the checks
that were blind to Hebrew now see it, on Hebrew fixtures shaped like a Reel
script and caption (made-up content).

Run:  python3 -m unittest discover -s tests/ig -v
"""

import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS = os.path.join(ROOT, "skills")
FIX = os.path.join(ROOT, "tests", "ig", "fixtures")
GOLD = os.path.join(ROOT, "tests", "ig", "golden")

TOOLS = {
    "hookscore": os.path.join(SKILLS, "ig-reel", "hookscore.py"),
    "beats": os.path.join(SKILLS, "ig-reel", "beats.py"),
    "caption": os.path.join(SKILLS, "ig-caption", "caption.py"),
    "humanize": os.path.join(SKILLS, "ig-human", "humanize.py"),
    "detect": os.path.join(SKILLS, "ig-human", "detect.py"),
}


def run(tool, *args, stdin=None):
    out = subprocess.run([sys.executable, "-I", TOOLS[tool], *args, "--json"],
                         input=stdin, capture_output=True, text=True, encoding="utf-8")
    return json.loads(out.stdout)


def fix(name):
    return os.path.join(FIX, name)


def gold(name):
    with open(os.path.join(GOLD, name), encoding="utf-8") as fh:
        return json.load(fh)


class EnglishUnchanged(unittest.TestCase):
    def test_hookscore(self):
        self.assertEqual(run("hookscore", fix("hooks-en.txt")), gold("hookscore-en.json"))

    def test_beats(self):
        self.assertEqual(run("beats", fix("script-en.txt"), "--target", "30"), gold("beats-en.json"))

    def test_caption(self):
        self.assertEqual(run("caption", fix("caption-en.txt"),
                             "--keywords", "client contracts,freelance pricing"),
                         gold("caption-en.json"))

    def test_humanize(self):
        self.assertEqual(run("humanize", fix("draft-en.txt")), gold("humanize-en.json"))

    def test_detect(self):
        self.assertEqual(run("detect", fix("draft-en.txt")), gold("detect-en.json"))


class HebrewSeen(unittest.TestCase):
    def test_beats_counts_and_times_hebrew(self):
        a = run("beats", fix("script-he.txt"), "--target", "25")
        self.assertEqual(a["wpm"], 130)
        self.assertEqual(a["total_words"], 53)   # str.split() count of the script
        self.assertGreater(a["total_seconds"], 20)
        self.assertTrue(any("Possible loop by root" in n for n in a["notes"]), a["notes"])

    def test_beats_exact_word_loop_through_prefix(self):
        a = run("beats", "-", stdin="תפסיקו לדלג על החימום לפני ריצה.\nהפציעה הבאה אולי שלכם. וחימום לוקח חמש דקות.\n")
        self.assertTrue(any(n.startswith("Loops:") for n in a["notes"]), a["notes"])

    def test_hookscore_hebrew_marks_english_checks_na(self):
        r = run("hookscore", "--hook", "חסכתי 40 שעות. בלי לגייס אף אחד.")
        self.assertIsNone(r["checks"]["STAKES"]["score"])
        self.assertIsNone(r["checks"]["ADDRESS"]["score"])
        self.assertEqual(r["checks"]["LENGTH"]["score"], 100.0)
        self.assertEqual(r["checks"]["SPECIFICITY"]["score"], 75.0)
        self.assertEqual(r["checks"]["FRONTLOAD"]["score"], 100.0)

    def test_hookscore_hebrew_spoken_number(self):
        r = run("hookscore", "--hook", "הכנתי את העוגה הזאת בעשרים דקות בלבד.")
        self.assertGreaterEqual(r["checks"]["SPECIFICITY"]["score"], 75.0)

    def test_caption_counts_hebrew_tags_and_asks(self):
        before = run("caption", fix("caption-he-before.txt"))
        self.assertEqual(len(before["hashtags"]), 8)
        self.assertEqual(sorted(before["asks"]), ["answer a question", "link in bio"])
        after = run("caption", fix("caption-he-after.txt"))
        self.assertEqual(len(after["hashtags"]), 5)
        self.assertEqual(after["asks"], ["link in bio"])

    def test_humanize_keeps_rlm_in_hebrew_only(self):
        he = run("humanize", "-", stdin="‏20 דקות. בלי לשחזר את הבעיה​.\n")
        self.assertIn("‏", he["text"])
        self.assertNotIn("​", he["text"])
        en = run("humanize", "-", stdin="‏20 minutes. No repro needed.\n")
        self.assertNotIn("‏", en["text"])

    def test_detect_hebrew_marks_english_checks_na(self):
        with open(fix("script-he.txt"), encoding="utf-8") as fh:
            r = run("detect", "-", stdin=fh.read())
        self.assertIsNone(r["checks"]["SLOP DENSITY"]["score"])
        self.assertIsNone(r["checks"]["VOICE"]["score"])
        self.assertIsNotNone(r["checks"]["BURSTINESS"]["score"])

    def test_niqqud_never_changes_a_score(self):
        plain = "תיקנתי באג של שבוע שלם, בעשרים דקות. בלי לשחזר את הבעיה. תוך חמש דקות הדיבאגר הראה את השורה. הקוד הבא שיתוקן, אולי שלכם.\n"
        marked = "תִּקַּנְתִּי באג של שבוע שלם, בְּעֶשְׂרִים דקות. בלי לשחזר את הבעיה. תוך חמש דקות הדיבאגר הֶרְאָה את השורה. הקוד הבא שֶׁיְּתֻקַּן, אולי שלכם.\n"
        for tool in ("hookscore", "detect"):
            a = run(tool, "-", stdin=plain)
            b = run(tool, "-", stdin=marked)
            pick = lambda r: {k: v["score"] for k, v in r["checks"].items()}
            self.assertEqual(pick(a), pick(b), tool)
        self.assertEqual(run("beats", "-", stdin=plain)["total_words"],
                         run("beats", "-", stdin=marked)["total_words"])


if __name__ == "__main__":
    unittest.main()
