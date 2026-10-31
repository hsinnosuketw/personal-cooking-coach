"""Recipe -> ordered steps with verb/noun pairs (Strategy pattern, design doc section 3).

  HDEpicExtractor   annotated steps from HD-EPIC: each step's pairs are the
                    main actions narrated inside its step/prep time spans
  ManualRecipeExtractor  a small JSON written by hand (e.g. your own video)
  NIMRecipeExtractor     a vision-language model on NVIDIA NIM writes the
                    steps and pairs from a recipe request (and optional
                    reference images); needs NVIDIA_API_KEY

Pairs use EK100 class keys ("cut", "onion"), the vocabulary the V-JEPA 2
probe predicts in; pairs outside it are dropped and counted.
"""
from __future__ import annotations

import base64
import json
import os
import pickle
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Protocol

import pandas as pd

from .domain import StepSpec
from .vocab import CACHE, Vocab

HD_DIR = CACHE / "hd-epic"
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NIM_MODEL = "meta/llama-3.2-90b-vision-instruct"


class IRecipeExtractor(Protocol):
    def extract_steps(self, recipe: str) -> list[StepSpec]: ...


class _PandasOnly(pickle.Unpickler):
    """HD-EPIC ships narrations only as a pickle; refuse anything but pandas/numpy
    classes so a tampered download can't run code."""

    def find_class(self, module, name):
        if module.split(".")[0] in ("pandas", "numpy"):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"blocked {module}.{name} in narrations pickle")


def load_narrations(path: Path = HD_DIR / "HD_EPIC_Narrations.pkl") -> pd.DataFrame:
    with open(path, "rb") as f:
        return _PandasOnly(f).load()


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


class HDEpicExtractor:
    """recipe = an HD-EPIC recipe id such as "P08_R03"."""

    def __init__(self, vocab: Vocab, hd_dir: Path = HD_DIR, narrations: pd.DataFrame | None = None):
        self.vocab = vocab
        self.recipes = json.loads((hd_dir / "complete_recipes.json").read_text(encoding="utf-8"))
        self.narr = narrations if narrations is not None else load_narrations(hd_dir / "HD_EPIC_Narrations.pkl")
        ek = CACHE
        self.verb_key = pd.read_csv(ek / "EPIC_100_verb_classes.csv").set_index("id").key.to_dict()
        self.noun_key = pd.read_csv(ek / "EPIC_100_noun_classes.csv").set_index("id").key.to_dict()
        self.dropped = 0

    def spans(self, recipe: str, capture: int = 0) -> dict[str, list[tuple[str, float, float]]]:
        """step id -> [(video, start, end)] from step_times and prep_times."""
        cap = self.recipes[recipe]["captures"][capture]
        out: dict[str, list] = defaultdict(list)
        for kind in ("step_times", "prep_times"):
            for sid, segs in cap.get(kind, {}).items():
                out[sid] += [(s["video"], float(s["start"]), float(s["end"])) for s in segs]
        return out

    def extract_steps(self, recipe: str, capture: int = 0) -> list[StepSpec]:
        steps = self.recipes[recipe]["steps"]
        spans = self.spans(recipe, capture)
        videos = {v for segs in spans.values() for v, _, _ in segs}
        narr = self.narr[self.narr.video_id.isin(videos)]
        out = []
        for order, (sid, text) in enumerate(steps.items()):
            weights: dict[tuple[str, str], float] = defaultdict(float)
            for video, s0, s1 in spans.get(sid, []):
                rows = narr[(narr.video_id == video) & (narr.end_timestamp > s0) & (narr.start_timestamp < s1)]
                for r in rows.itertuples():
                    w = _overlap(r.start_timestamp, r.end_timestamp, s0, s1)
                    for v, n in r.main_action_classes:
                        vk, nk = self.verb_key.get(v), self.noun_key.get(n)
                        if vk in self.vocab.verb_row and nk in self.vocab.noun_row:
                            weights[(vk, nk)] += w
                        else:
                            self.dropped += 1
            out.append(StepSpec(sid, text.strip(), order, tuple((v, n, round(w, 3)) for (v, n), w in weights.items())))
        return out


class ManualRecipeExtractor:
    """recipe = path to {"steps": [{"id", "text", "pairs": [["cut", "onion"], ...]}]}."""

    def __init__(self, vocab: Vocab):
        self.vocab = vocab
        self.dropped = 0

    def extract_steps(self, recipe: str) -> list[StepSpec]:
        data = json.loads(Path(recipe).read_text(encoding="utf-8"))
        return [StepSpec(s.get("id", f"S{i + 1:02d}"), s["text"], i, self._keep(s.get("pairs", [])))
                for i, s in enumerate(data["steps"])]

    def _keep(self, pairs) -> tuple:
        kept = tuple((v, n, 1.0) for v, n in pairs if v in self.vocab.verb_row and n in self.vocab.noun_row)
        self.dropped += len(pairs) - len(kept)
        return kept


class NIMRecipeExtractor:
    """A VLM on NVIDIA's hosted NIM (OpenAI-compatible) writes the steps.

    recipe = a request such as "scrambled eggs with onion" (see hd_request()
    for one built from an HD-EPIC recipe). Reference images (e.g. a photo of
    the ingredients) are optional. Tags are mapped onto the probe's classes
    through EPIC-KITCHENS' synonym lists (whisk -> mix); tags with no class
    are dropped and counted. n_steps fixes the step count so the answer can
    be compared row by row with another source's steps.

    tag_steps() is the other mode: the recipe text is given (as a user would
    hand it over) and the VLM only writes each step's action tags.
    distinct=True asks for tags that tell the steps apart. It sounds right
    (a tracker can't separate steps that all say "mix egg") but measured
    worse on P08 (compare_vlm.py): the specific actions it picks are the
    ones the EK100 probe reads poorly on HD-EPIC. So it is off by default.
    """

    def __init__(self, vocab: Vocab, model: str = NIM_MODEL, images: list[Path] = (), timeout: float = 180.0,
                 retries: int = 1, post=None, n_steps: int | None = None, distinct: bool = False,
                 hand_level: bool = False, frequencies: tuple[dict, dict] | None = None):
        self.vocab, self.model, self.images, self.n_steps = vocab, model, list(images), n_steps
        self.distinct, self.hand_level, self.frequencies = distinct, hand_level, frequencies
        self.timeout, self.retries = timeout, retries
        self.post = post or self._post  # tests pass a fake transport
        self.dropped = 0
        self.calls = self.prompt_tokens = self.completion_tokens = 0
        self.last_raw = ""                     # the model's last answer, verbatim
        self.rejected: list[tuple[int, str, str]] = []  # (step order, verb, noun) outside the vocabulary
        self.mapped: list[tuple[int, str, str]] = []    # (step order, "whisk egg", "mix egg") synonym rewrites

    DISTINCT = (
        " Choose tags that tell the steps apart, because a camera will use them to recognise which step the "
        "cook is on: never give the same [verb, noun] pair to two steps; prefer what is specific to the step "
        "(crack egg, spray pan, peel onion, grate cheese) over generic actions that happen in many steps (mix, "
        "take, put) unless that generic action is the step's main action; include the hand actions a camera "
        "would see while doing the step, such as taking out or putting away its own container or utensil.")

    HAND = (
        " Describe what the cook's HANDS do, the way a head-mounted camera sees it, not what the recipe says "
        "happens to the food. Recipe verbs such as add, season, fold, cook or serve are rarely visible as such: "
        "write the hand movements instead. For example, for making tea and a salad (a different dish, only to "
        "show the level of detail): open the cupboard, take the cup, take the kettle, put the kettle at the tap, "
        "turn-on the tap, put the teabag, pour the water, open the fridge, take the tomato, take the knife, cut "
        "the tomato, wash the knife, put the plate. Include fetching and putting "
        "away the step's containers, tools and ingredients. Give 3-6 pairs per step. The verbs are listed most "
        "frequent first: prefer the frequent ones when they describe the movement.")

    def _vocab_lists(self) -> str:
        if self.hand_level and self.frequencies:
            vf, nf = self.frequencies
            verbs = sorted(self.vocab.verb_row, key=lambda w: -vf.get(w, 0))
            nouns = sorted(self.vocab.noun_row, key=lambda w: -nf.get(w, 0))
            return ("using ONLY these verbs (most frequent first):\n" + ", ".join(verbs) +
                    "\nand ONLY these nouns (most frequent first):\n" + ", ".join(nouns))
        return ("using ONLY these verbs:\n" + ", ".join(sorted(self.vocab.verb_row)) +
                "\nand ONLY these nouns:\n" + ", ".join(sorted(self.vocab.noun_row)))

    def _prompt(self, recipe: str) -> str:
        return (
            f"Write the cooking steps for: {recipe}.\n"
            "Return only JSON: {\"steps\": [{\"text\": \"...\", \"pairs\": [[verb, noun], ...]}]} with "
            + (f"exactly {self.n_steps} steps" if self.n_steps else "4-10 steps") +
            " in cooking order. Write each step like a recipe card: 1-3 sentences with the utensil, the heat "
            "level and the cue for when it is done. For each step list the 1-4 hand actions it involves as "
            "[verb, noun] pairs," + (self.DISTINCT if self.distinct else "") + " Use " + self._vocab_lists())

    def _tag_prompt(self, name: str, texts: list[str]) -> str:
        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
        return (
            f"Here is a recipe for {name} with {len(texts)} steps:\n{numbered}\n\n"
            "For each step, list the 2-5 hand actions a head-mounted camera would see while the cook does it, as "
            "[verb, noun] pairs. Return only JSON: {\"steps\": [{\"text\": \"<the step, copied>\", \"pairs\": "
            f"[[verb, noun], ...]}}]}} with exactly {len(texts)} steps in the same order." +
            (self.HAND if self.hand_level else "") + (self.DISTINCT if self.distinct else "") +
            " Use " + self._vocab_lists())

    def tag_steps(self, name: str, texts: list[str]) -> list[StepSpec]:
        """The recipe's own step texts are kept; the VLM only supplies the tags."""
        steps = self._ask(self._tag_prompt(name, texts))
        if len(steps) != len(texts):
            raise ValueError(f"asked for {len(texts)} steps, got {len(steps)}")
        return [StepSpec(s.step_id, t.strip(), s.order, s.pairs) for s, t in zip(steps, texts)]

    def _post(self, body: dict) -> dict:
        key = os.environ.get("NVIDIA_API_KEY")
        if not key:
            raise RuntimeError("NVIDIA_API_KEY is not set (get one at build.nvidia.com)")
        data = json.dumps(body).encode()
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(NIM_URL, data=data, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and attempt < self.retries:
                    time.sleep(1.0 + attempt)
                    continue
                raise
            except TimeoutError:  # a long answer from a busy shared endpoint
                if attempt < self.retries:
                    continue
                raise

    def extract_steps(self, recipe: str) -> list[StepSpec]:
        return self._ask(self._prompt(recipe))

    def _ask(self, prompt: str) -> list[StepSpec]:
        content = [{"type": "text", "text": prompt}]
        for img in self.images:
            b64 = base64.b64encode(Path(img).read_bytes()).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        last_error = None
        for _ in range(self.retries + 1):
            data = self.post({"model": self.model, "messages": [{"role": "user", "content": content}],
                              "temperature": 0.2, "max_tokens": 1500})
            self.calls += 1
            usage = data.get("usage") or {}
            self.prompt_tokens += usage.get("prompt_tokens", 0)
            self.completion_tokens += usage.get("completion_tokens", 0)
            try:
                self.last_raw = data["choices"][0]["message"]["content"]
                return self._parse(self.last_raw)
            except (ValueError, KeyError, TypeError) as e:
                last_error = e  # malformed JSON: ask once more
        raise ValueError(f"NIM answer was not usable JSON: {last_error}")

    def _parse(self, text: str) -> list[StepSpec]:
        m = re.search(r"\{.*\}", text, re.S)  # models sometimes wrap JSON in prose or code fences
        steps = json.loads(m.group(0) if m else text)["steps"]
        out = []
        for i, s in enumerate(steps):
            kept = []
            for v, n in s.get("pairs", []):
                v, n = str(v).strip().lower(), str(n).strip().lower()
                cv, cn = self.vocab.canon("verb", v), self.vocab.canon("noun", n)
                if cv is None or cn is None:
                    self.dropped += 1
                    self.rejected.append((i, v, n))
                    continue
                if (cv, cn) != (v, n):
                    self.mapped.append((i, f"{v} {n}", f"{cv} {cn}"))
                if (cv, cn, 1.0) not in kept:
                    kept.append((cv, cn, 1.0))
            kept = tuple(kept)
            out.append(StepSpec(f"S{i + 1:02d}", str(s["text"]).strip(), i, kept))
        if not out:
            raise ValueError("no steps")
        return out


def hd_request(recipe: dict) -> str:
    """A request built only from an HD-EPIC recipe's name and ingredient names,
    so the VLM gets what a user would type, not the annotated steps."""
    names = []
    for cap in recipe["captures"]:
        for ing in cap["ingredients"].values():
            if ing["name"] not in names:
                names.append(ing["name"])
    return f"{recipe['name']} (ingredients: {', '.join(names)})"
