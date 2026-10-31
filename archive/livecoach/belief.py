"""Skill-belief updates (plan E01/E04/E07/E10).

Prompts, acknowledgements, self-reports and ignored advice are recorded
but never raise a level: only observed outcomes do. Beliefs are keyed by
skill, not recipe, so Curry reads Pasta evidence, and every item keeps the
recipe and step it came from.
"""
from __future__ import annotations

from .recipes import SKILLS
from .schema import SKILL_ORDER, Evidence, EvidenceKind, SkillBelief, SkillLevel

RAISES_TO = {
    EvidenceKind.observed_guided_success: SkillLevel.guided_success,
    EvidenceKind.observed_independent_success: SkillLevel.independent_success,
}
TEACHING_VALUE = {SkillLevel.unknown: 1.0, SkillLevel.needs_prompt: 1.0,
                  SkillLevel.guided_success: 0.5, SkillLevel.independent_success: 0.0}


def new_beliefs() -> dict[str, SkillBelief]:
    return {k: SkillBelief(skill_id=k) for k in SKILLS}


def add_evidence(beliefs: dict[str, SkillBelief], ev: Evidence) -> None:
    b = beliefs[ev.skill_id]
    b.evidence.append(ev)
    if ev.kind in RAISES_TO:
        if SKILL_ORDER.index(RAISES_TO[ev.kind]) > SKILL_ORDER.index(b.level):
            b.level = RAISES_TO[ev.kind]
    elif ev.kind == EvidenceKind.observed_failure:
        # one level down, never below needs_prompt (a failure is still information)
        b.level = SKILL_ORDER[max(1, SKILL_ORDER.index(b.level) - 1)]


def teaching_value(beliefs: dict[str, SkillBelief], skill_id: str | None) -> float:
    return TEACHING_VALUE[beliefs[skill_id].level] if skill_id else 0.0


def version(beliefs: dict[str, SkillBelief], skill_ids) -> tuple:
    """Cache-key part: the levels that shape coaching for these skills."""
    return tuple(beliefs[k].level.value for k in skill_ids)
