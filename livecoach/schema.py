"""Data contracts for the live cooking coach (plan items B05-B10).

Every module exchanges these models and server.py exports their JSON
Schema, so camera, transcript, manual and replay inputs share one format.
Three separations from the plan are enforced by type:
  * kitchen facts carry a status and source; unknowns stay unknown;
  * predictions (WMPrediction) never enter KitchenState;
  * a prompt, an acknowledgement and an observed success are different
    kinds of Evidence, so only observed outcomes move a skill level.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field

Source = Literal["camera", "transcript", "manual", "replay"]
Value = Union[bool, float, str]


class FactStatus(str, Enum):
    observed = "observed"            # camera, replay, or a person entering what they see
    self_reported = "self_reported"  # the learner said so
    unknown = "unknown"
    conflict = "conflict"            # two sources disagree; both values are kept


class Fact(BaseModel):
    value: Value | None = None
    status: FactStatus = FactStatus.unknown
    source: Source | None = None
    ts: float = 0.0
    alt: Value | None = None         # the competing value while status is conflict
    alt_source: Source | None = None


class ObservationEvent(BaseModel):
    event_id: str
    ts: float
    source: Source
    facts: dict[str, Value] = Field(default_factory=dict)
    step_id: str | None = None       # the learner moved to this recipe step
    transcript: str | None = None


class KitchenState(BaseModel):
    recipe_id: str
    step_id: str
    version: int = 0
    step_started_ts: float = 0.0
    facts: dict[str, Fact] = Field(default_factory=dict)


class SkillLevel(str, Enum):
    unknown = "unknown"
    needs_prompt = "needs_prompt"
    guided_success = "guided_success"
    independent_success = "independent_success"


SKILL_ORDER = [SkillLevel.unknown, SkillLevel.needs_prompt,
               SkillLevel.guided_success, SkillLevel.independent_success]


class EvidenceKind(str, Enum):
    prompt_given = "prompt_given"
    prompt_acknowledged = "prompt_acknowledged"
    self_reported_done = "self_reported_done"
    observed_guided_success = "observed_guided_success"
    observed_independent_success = "observed_independent_success"
    observed_failure = "observed_failure"
    not_followed = "not_followed"


class Evidence(BaseModel):
    kind: EvidenceKind
    skill_id: str
    recipe_id: str
    step_id: str
    ts: float
    ref: str = ""                    # the event or decision that produced it


class SkillBelief(BaseModel):
    skill_id: str
    level: SkillLevel = SkillLevel.unknown
    evidence: list[Evidence] = Field(default_factory=list)


CandidateKind = Literal["adjust", "ask", "observe", "advance"]


class Candidate(BaseModel):
    candidate_id: str
    kind: CandidateKind
    skill_id: str | None = None
    label: str
    feasible: bool = True
    reason_infeasible: str | None = None


class WMPrediction(BaseModel):
    candidate_id: str
    horizon_s: int
    primary_outcome: str
    alternative_outcome: str
    burn_risk: float                 # 0..1
    target_gap: float                # 0..1 distance from the step's target state
    confidence: Literal["low", "medium", "high"]  # rubric, not a calibrated probability
    predicted_skill_effect: str
    assumptions: list[str] = Field(default_factory=list)


class Decision(BaseModel):
    decision_id: str
    candidate_id: str
    kind: CandidateKind
    source: Literal["rule", "cache", "model"]
    action_line: str
    reason_line: str
    speak: bool                      # False: keep watching quietly
    state_version: int
    ts: float


class LearnerResponse(BaseModel):
    decision_id: str
    kind: Literal["received", "acknowledged", "self_reported_done",
                  "observed_success", "not_followed"]
    ts: float
