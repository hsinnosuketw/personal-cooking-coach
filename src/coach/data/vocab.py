"""The EK100 probe's label space, without importing torch.

The probe's output rows follow the order filter_annotations() builds from
EPIC_100_train.csv (vjepa2 evals/action_anticipation_frozen/epickitchens.py),
so the maps are rebuilt the same way here. HD-EPIC reuses the EK100 class
ids for every verb and noun the probe knows (checked 2026-10-31).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..config import DATA_RAW as CACHE  # downloads (python3 -m coach.data.fetch)


def class_maps(train_csv: Path) -> dict:
    """Probe label order, built exactly as the repo's filter_annotations() does."""
    tdf = pd.read_csv(train_csv)
    tactions = set([(v, n) for v, n in zip(tdf["verb_class"].values, tdf["noun_class"].values)])
    tverbs = set([v for v, _ in tactions])
    tnouns = set([n for _, n in tactions])
    return dict(verbs={k: i for i, k in enumerate(tverbs)}, nouns={k: i for i, k in enumerate(tnouns)},
                actions={k: i for i, k in enumerate(tactions)})


@dataclass(frozen=True)
class Vocab:
    """Class keys ("cut", "onion") <-> probe output rows.

    A word "is known" when it maps to a row of the probe's output layer:
    either it is a class key, or EPIC-KITCHENS lists it among that class's
    instances (synonyms its annotators merged, e.g. whisk -> mix, chop -> cut).
    """
    verb_row: dict[str, int]
    noun_row: dict[str, int]
    verb_alias: dict[str, str] = field(default_factory=dict)
    noun_alias: dict[str, str] = field(default_factory=dict)

    def canon(self, kind: str, word: str) -> str | None:
        """The probe's class key for a free-text verb or noun, or None if it has no row."""
        w = " ".join(str(word).strip().lower().replace("-", " ").split())
        rows, alias = (self.verb_row, self.verb_alias) if kind == "verb" else (self.noun_row, self.noun_alias)
        key = w.replace(" ", ":") if w.replace(" ", ":") in rows else w
        if key in rows:
            return key
        if kind == "verb":
            return alias.get(w) or (alias.get(w.split(" ")[0]) if w else None)
        # nouns: the word, its singular, then the head noun (last word: "cottage cheese" -> cheese)
        for cand in (w, w.split(" ")[-1]) if w else ():
            for form in (cand, cand[:-1] if cand.endswith("s") else None, cand[:-2] if cand.endswith("es") else None,
                         cand[:-3] + "y" if cand.endswith("ies") else None):
                if form and (form in rows or form in alias):
                    return form if form in rows else alias[form]
        return None

    @property
    def n_verbs(self) -> int:
        return len(self.verb_row)

    @property
    def n_nouns(self) -> int:
        return len(self.noun_row)

    @classmethod
    def load(cls, cache: Path = CACHE) -> "Vocab":
        maps = class_maps(cache / "EPIC_100_train.csv")
        vdf = pd.read_csv(cache / "EPIC_100_verb_classes.csv").set_index("id")
        ndf = pd.read_csv(cache / "EPIC_100_noun_classes.csv").set_index("id")
        verb_row = {vdf.key[c]: r for c, r in maps["verbs"].items()}
        noun_row = {ndf.key[c]: r for c, r in maps["nouns"].items()}
        return cls(verb_row, noun_row, _aliases(vdf, verb_row, first_word=True), _aliases(ndf, noun_row))


def _aliases(df: pd.DataFrame, rows: dict[str, int], first_word: bool = False) -> dict[str, str]:
    """instance word -> class key, for classes the probe has a row for. When a
    word is an instance of several classes, the first class (lowest id) wins."""
    out: dict[str, str] = {}
    for key, instances in zip(df.key, df.instances):
        if key not in rows:
            continue
        for inst in ast.literal_eval(instances):
            w = " ".join(inst.lower().replace("-", " ").split())
            out.setdefault(w, key)
            if first_word:
                out.setdefault(w.split(" ")[0], key)
    return out


def class_frequencies(cache: Path = CACHE) -> tuple[dict[str, int], dict[str, int]]:
    """How often each verb and noun class is narrated in EPIC_100_train.csv: what
    the probe saw most while it was trained (not taken from any test video)."""
    t = pd.read_csv(cache / "EPIC_100_train.csv")
    vkey = pd.read_csv(cache / "EPIC_100_verb_classes.csv").set_index("id").key
    nkey = pd.read_csv(cache / "EPIC_100_noun_classes.csv").set_index("id").key
    return ({vkey[c]: int(n) for c, n in t.verb_class.value_counts().items()},
            {nkey[c]: int(n) for c, n in t.noun_class.value_counts().items()})
