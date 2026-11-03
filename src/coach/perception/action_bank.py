"""Turn a recipe's steps into stacked signature matrices once, offline (design doc section 3)."""
from __future__ import annotations

import numpy as np

from ..domain import CandidateAction, StepSpec
from ..data.extractors import IRecipeExtractor
from ..data.vocab import Vocab

SMOOTH = 0.02  # share of each signature spread evenly, so one unseen verb can't zero a step out


def signature(pairs, index: dict[str, int], which: int) -> np.ndarray:
    sig = np.zeros(len(index))
    for p in pairs:
        sig[index[p[which]]] += p[2]
    total = sig.sum()
    uniform = np.full(len(index), 1.0 / len(index))
    if total <= 0:
        return uniform  # a step with no known actions says nothing about verbs/nouns
    return (1 - SMOOTH) * sig / total + SMOOTH * uniform


class ActionBankRepository:
    def __init__(self, vocab: Vocab):
        self.vocab = vocab
        self.candidates: list[CandidateAction] = []
        self.verb_matrix = np.zeros((0, vocab.n_verbs))
        self.noun_matrix = np.zeros((0, vocab.n_nouns))

    def initialize_bank(self, recipe: str, extractor: IRecipeExtractor) -> "ActionBankRepository":
        return self.from_steps(extractor.extract_steps(recipe))

    def from_steps(self, steps: list[StepSpec]) -> "ActionBankRepository":
        self.candidates = [CandidateAction(s.step_id, s.text, s.order,
                                           signature(s.pairs, self.vocab.verb_row, 0),
                                           signature(s.pairs, self.vocab.noun_row, 1)) for s in steps]
        self.verb_matrix = np.stack([c.verb_sig for c in self.candidates])
        self.noun_matrix = np.stack([c.noun_sig for c in self.candidates])
        return self

    def get_all_candidates(self) -> list[CandidateAction]:
        return list(self.candidates)

    def get_batched_embeddings(self) -> tuple[np.ndarray, np.ndarray]:
        return self.verb_matrix, self.noun_matrix
