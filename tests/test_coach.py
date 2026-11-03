"""Checks for the V-JEPA 2 recipe guide's offline layer. Run: python3 tests/test_coach.py

No torch, no network: the NIM extractor runs against a fake transport.
Tests that need the downloaded EK100/HD-EPIC files skip when they're absent.
"""
import io
import json
import os
import pickle
import tempfile

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # runs without pip install -e .

from coach.data import extractors
from coach.data.vocab import CACHE, Vocab
from coach.domain import Prediction, StepSpec
from coach.perception.action_bank import ActionBankRepository
from coach.perception.scorer import LatentStateScorer, match_scores

TINY = Vocab(verb_row={"take": 0, "cut": 1, "pour": 2, "stir": 3},
             noun_row={"egg": 0, "onion": 1, "pan": 2, "knife": 3, "bowl": 4})
STEPS = [StepSpec("S01", "Crack the eggs into a bowl", 0, (("take", "egg", 2.0), ("pour", "bowl", 1.0))),
         StepSpec("S02", "Chop the onion", 1, (("cut", "onion", 3.0), ("take", "knife", 1.0))),
         StepSpec("S03", "Stir the eggs in the pan", 2, (("stir", "pan", 2.0), ("pour", "egg", 1.0)))]
HAVE_DATA = (CACHE / "EPIC_100_train.csv").exists() and (CACHE / "hd-epic" / "HD_EPIC_Narrations.pkl").exists()


def bank():
    return ActionBankRepository(TINY).from_steps(STEPS)


def onehot(n, *idx, p=0.9):
    v = np.full(n, (1 - p) / n)
    for i in idx:
        v[i] += p / len(idx)
    return v


def test_signatures_are_distributions_and_follow_the_pairs():
    b = bank()
    V, Nn = b.get_batched_embeddings()
    assert V.shape == (3, 4) and Nn.shape == (3, 5)
    assert np.allclose(V.sum(1), 1) and np.allclose(Nn.sum(1), 1)
    assert V[1].argmax() == TINY.verb_row["cut"] and Nn[1].argmax() == TINY.noun_row["onion"]
    empty = ActionBankRepository(TINY).from_steps([StepSpec("X", "rest", 0, ())])
    assert np.allclose(empty.verb_matrix[0], 0.25), "a step with no known actions is uniform"


def test_batched_scores_equal_scoring_each_candidate_alone():
    b = bank()
    rng = np.random.default_rng(0)
    pv, pn = rng.random((7, 4)), rng.random((7, 5))
    batched = match_scores(b, pv, pn)
    for t in range(7):
        nv, nn = pv[t] / pv[t].sum(), pn[t] / pn[t].sum()
        for k, c in enumerate(b.get_all_candidates()):
            assert np.isclose(batched[t, k], np.log(nv @ c.verb_sig) + np.log(nn @ c.noun_sig))


def test_guide_pauses_only_after_a_steady_change_of_step():
    s = LatentStateScorer(bank(), patience=2)
    crack = Prediction(0, onehot(4, 0, 2), onehot(5, 0, 4))
    chop = Prediction(0, onehot(4, 1), onehot(5, 1, 3))
    assert not s.evaluate(crack).should_pause
    r = s.evaluate(crack)
    assert r.should_pause and r.action.action_id == "S01"
    assert not s.evaluate(chop).should_pause, "one tick of new evidence is not enough"
    assert not s.evaluate(crack).should_pause and s.current == 0, "a blip resets the streak"
    s.evaluate(chop)
    r = s.evaluate(chop)
    assert r.should_pause and r.action.action_id == "S02"
    assert not s.evaluate(chop).should_pause, "staying on the same step never pauses again"


def test_nim_extractor_parses_fenced_json_drops_unknown_keys_and_retries():
    answers = iter([
        {"choices": [{"message": {"content": "Sure! not json"}}]},
        {"choices": [{"message": {"content": "```json\n" + json.dumps({"steps": [
            {"text": "Crack eggs", "pairs": [["take", "egg"], ["fling", "egg"]]},
            {"text": "Chop onion", "pairs": [["Cut", "Onion"]]}]}) + "\n```"}}],
         "usage": {"prompt_tokens": 900, "completion_tokens": 80}},
    ])
    sent = []
    ex = extractors.NIMRecipeExtractor(TINY, post=lambda body: (sent.append(body), next(answers))[1])
    steps = ex.extract_steps("scrambled eggs")
    assert [s.text for s in steps] == ["Crack eggs", "Chop onion"]
    assert steps[0].pairs == (("take", "egg", 1.0),) and steps[1].pairs == (("cut", "onion", 1.0),)
    assert ex.dropped == 1 and ex.calls == 2 and ex.prompt_tokens == 900
    assert sent[0]["model"] == extractors.NIM_MODEL and "ONLY these verbs" in sent[0]["messages"][0]["content"][0]["text"]


def test_free_text_words_map_onto_the_probe_classes_through_synonyms():
    v = Vocab({"mix": 0, "cut": 1, "pick:up": 2}, {"egg": 0, "shell:egg": 1},
              verb_alias={"whisk": "mix", "chop": "cut"}, noun_alias={"egg shell": "shell:egg"})
    assert v.canon("verb", "Whisk") == "mix" and v.canon("verb", "chop finely") == "cut"
    assert v.canon("verb", "pick up") == "pick:up" and v.canon("noun", "egg shell") == "shell:egg"
    assert v.canon("verb", "heat") is None
    ex = extractors.NIMRecipeExtractor(v, post=lambda body: {"choices": [{"message": {"content": json.dumps(
        {"steps": [{"text": "Beat eggs", "pairs": [["whisk", "egg"], ["mix", "egg"], ["heat", "egg"]]}]})}}]})
    steps = ex.extract_steps("eggs")
    assert steps[0].pairs == (("mix", "egg", 1.0),), "synonym and key collapse into one tag"
    assert ex.mapped == [(0, "whisk egg", "mix egg")] and ex.rejected == [(0, "heat", "egg")]


def test_nim_extractor_needs_a_key_and_never_calls_out_without_one():
    old = os.environ.pop("NVIDIA_API_KEY", None)
    try:
        extractors.NIMRecipeExtractor(TINY, retries=0).extract_steps("eggs")
        raise AssertionError("ran without a key")
    except RuntimeError as e:
        assert "NVIDIA_API_KEY" in str(e)
    finally:
        if old is not None:
            os.environ["NVIDIA_API_KEY"] = old


def test_manual_extractor_reads_json_and_keeps_known_pairs():
    path = os.path.join(tempfile.mkdtemp(), "r.json")
    with open(path, "w") as f:
        json.dump({"steps": [{"text": "Chop", "pairs": [["cut", "onion"], ["dice", "onion"]]}]}, f)
    ex = extractors.ManualRecipeExtractor(TINY)
    assert ex.extract_steps(path)[0].pairs == (("cut", "onion", 1.0),) and ex.dropped == 1


def test_narrations_loader_refuses_pickles_that_would_run_code():
    class Evil:
        def __reduce__(self):
            return (os.system, ("echo pwned",))
    try:
        extractors._PandasOnly(io.BytesIO(pickle.dumps(Evil()))).load()
        raise AssertionError("loaded a code-running pickle")
    except pickle.UnpicklingError as e:
        assert "blocked" in str(e)


def test_real_vocab_and_hd_epic_recipe():
    if not HAVE_DATA:
        print("  (skipped: run python3 -m coach.data.fetch --annotations-only for the EK100 and HD-EPIC files)")
        return
    vocab = Vocab.load()
    assert (vocab.n_verbs, vocab.n_nouns) == (97, 289)
    ex = extractors.HDEpicExtractor(vocab)
    steps = ex.extract_steps("P08_R03")
    assert len(steps) == 7 and sum(bool(s.pairs) for s in steps) >= 5
    onion_step = next(s for s in steps if "onion" in s.text.lower())
    assert any(n == "onion" for _, n, _ in onion_step.pairs), onion_step


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} tests passed")
