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

    recipe = a request such as "scrambled eggs with onion". Reference images
    (e.g. a photo of the ingredients) are optional. The model must answer
    with EK100 verb and noun keys; anything else is dropped and counted.
    """

    def __init__(self, vocab: Vocab, model: str = NIM_MODEL, images: list[Path] = (), timeout: float = 180.0,
                 retries: int = 1, post=None):
        self.vocab, self.model, self.images = vocab, model, list(images)
        self.timeout, self.retries = timeout, retries
        self.post = post or self._post  # tests pass a fake transport
        self.dropped = 0
        self.calls = self.prompt_tokens = self.completion_tokens = 0

    def _prompt(self, recipe: str) -> str:
        return (
            f"Write the cooking steps for: {recipe}.\n"
            "Return only JSON: {\"steps\": [{\"text\": \"...\", \"pairs\": [[verb, noun], ...]}]} with 4-10 steps "
            "in cooking order. For each step list the 1-4 hand actions it involves as [verb, noun] pairs, using "
            "ONLY these verbs:\n" + ", ".join(sorted(self.vocab.verb_row)) +
            "\nand ONLY these nouns:\n" + ", ".join(sorted(self.vocab.noun_row)))

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
        content = [{"type": "text", "text": self._prompt(recipe)}]
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
                return self._parse(data["choices"][0]["message"]["content"])
            except (ValueError, KeyError, TypeError) as e:
                last_error = e  # malformed JSON: ask once more
        raise ValueError(f"NIM answer was not usable JSON: {last_error}")

    def _parse(self, text: str) -> list[StepSpec]:
        m = re.search(r"\{.*\}", text, re.S)  # models sometimes wrap JSON in prose or code fences
        steps = json.loads(m.group(0) if m else text)["steps"]
        out = []
        for i, s in enumerate(steps):
            pairs = [(str(v).strip().lower(), str(n).strip().lower()) for v, n in s.get("pairs", [])]
            kept = tuple((v, n, 1.0) for v, n in pairs if v in self.vocab.verb_row and n in self.vocab.noun_row)
            self.dropped += len(pairs) - len(kept)
            out.append(StepSpec(f"S{i + 1:02d}", str(s["text"]).strip(), i, kept))
        if not out:
            raise ValueError("no steps")
        return out
