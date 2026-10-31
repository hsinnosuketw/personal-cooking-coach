"""The EK100 probe's label space, without importing torch.

The probe's output rows follow the order filter_annotations() builds from
EPIC_100_train.csv (vjepa2 evals/action_anticipation_frozen/epickitchens.py),
so the maps are rebuilt the same way here. HD-EPIC reuses the EK100 class
ids for every verb and noun the probe knows (checked 2026-10-31).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).parent / "_cache"


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
    """Class keys ("cut", "onion") <-> probe output rows."""
    verb_row: dict[str, int]
    noun_row: dict[str, int]

    @property
    def n_verbs(self) -> int:
        return len(self.verb_row)

    @property
    def n_nouns(self) -> int:
        return len(self.noun_row)

    @classmethod
    def load(cls, cache: Path = CACHE) -> "Vocab":
        maps = class_maps(cache / "EPIC_100_train.csv")
        verbs = pd.read_csv(cache / "EPIC_100_verb_classes.csv").set_index("id").key
        nouns = pd.read_csv(cache / "EPIC_100_noun_classes.csv").set_index("id").key
        return cls(verb_row={verbs[c]: r for c, r in maps["verbs"].items()},
                   noun_row={nouns[c]: r for c, r in maps["nouns"].items()})
