"""coach.vision.checks with a fake vision model. Run: python3 tests/test_vision.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.vision.checks import LookSettings, Looker, check_prompt, frame_checked_starts, parse_status, parse_step


def test_answers_are_read_and_copied_option_lists_ignored():
    assert parse_status("**STATUS: In progress** eggs in a bowl") == "in progress"
    assert parse_status("STATUS: not started | in progress | done | can't tell") == "can't tell"
    assert parse_status("yes, the eggs are cracked", version=4) == "in progress"
    assert parse_step("STEP: 3 onions on the board", [1, 2]) == 2 and parse_step("STEP: 1", [1, 2]) is None
    assert "Step 2: Cut the onion" in check_prompt("start", 1, 70.0, "cut onion around 1:08", [], "Eggs",
                                                   ["Crack", "Cut the onion"], 20)


def test_a_start_waits_for_the_frames_and_answers_are_cached():
    asked = []
    def ask(img, prompt, k, t):
        asked.append((k, t))
        return "STATUS: in progress", 0.1, 0.5
    with tempfile.TemporaryDirectory() as d:
        look = Looker("fake", 2, Path(d) / "looks.json", lambda t: b"jpeg", ask, lambda *a: "prompt")
        probs = [[0.0], [0.5], [0.5], [0.5], [0.5]]
        ticks, looks = frame_checked_starts(range(5), probs, ["crack egg"], {"crack egg": [0]}, 2, 0.25, 2, look,
                                            LookSettings(), use_looks=True)
        assert [x["ledger"][0] for x in ticks] == ["not started", "not started", "not started", "in progress", "in progress"]
        assert [c["kind"] for c in looks] == ["start"] and asked == [(0, 2.0)]
        again = Looker("fake", 2, Path(d) / "looks.json", None, None, None)("start", 0, 2.0, "", [])
        assert again["status"] == "in progress"   # from the cache: no sheet, no model


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
