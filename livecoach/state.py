"""Kitchen-state reducer (plan D07/D08): events in, facts with provenance out.

Only ObservationEvents change the state; world-model predictions never do.
Two different sources disagreeing within CONFLICT_WINDOW_S keep both
values as a conflict, which planning treats like an unknown. Every applied
event bumps `version`, so a result computed for an older version is stale.
"""
from __future__ import annotations

from . import recipes
from .schema import Fact, FactStatus, KitchenState, ObservationEvent

CONFLICT_WINDOW_S = 20.0
CERTAIN = (FactStatus.observed, FactStatus.self_reported)


def initial_state(recipe_id: str, ts: float = 0.0) -> KitchenState:
    return KitchenState(recipe_id=recipe_id, step_id=recipes.first_step_id(recipe_id),
                        step_started_ts=ts)


def apply_event(state: KitchenState, ev: ObservationEvent) -> KitchenState:
    s = state.model_copy(deep=True)
    if ev.step_id and ev.step_id != s.step_id:
        recipes.step(s.recipe_id, ev.step_id)  # raises on an unknown step
        s.step_id, s.step_started_ts = ev.step_id, ev.ts
    status = FactStatus.self_reported if ev.source == "transcript" else FactStatus.observed
    for name, value in ev.facts.items():
        old = s.facts.get(name)
        if (old is not None and old.status in CERTAIN and old.value != value
                and old.source != ev.source and ev.ts - old.ts <= CONFLICT_WINDOW_S):
            s.facts[name] = Fact(value=value, status=FactStatus.conflict, source=ev.source,
                                 ts=ev.ts, alt=old.value, alt_source=old.source)
        else:
            s.facts[name] = Fact(value=value, status=status, source=ev.source, ts=ev.ts)
    s.version += 1
    return s


def known(state: KitchenState, name: str):
    """The fact's value when it is trustworthy, else None (unknown or conflict)."""
    f = state.facts.get(name)
    return f.value if f is not None and f.status in CERTAIN else None


def is_stale(result_version: int, state: KitchenState) -> bool:
    return result_version != state.version
