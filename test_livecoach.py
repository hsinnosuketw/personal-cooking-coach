"""Checks for the live cooking coach. Run: python3 test_livecoach.py"""
from livecoach import belief, candidates, onion, policy, recipes, state
from livecoach.provider import MockProvider
from livecoach.schema import (Evidence, EvidenceKind, FactStatus, LearnerResponse, ObservationEvent,
                              SkillLevel)
from livecoach.session import Session
from livecoach.world_model import WorldModel


def ev(i, source, ts, step_id=None, **facts):
    return ObservationEvent(event_id=f"e{i}", ts=ts, source=source, step_id=step_id, facts=facts)


def test_recipes_share_skill_ids_but_not_targets():
    pasta, curry = recipes.load("pasta_pomodoro"), recipes.load("curry_onion")
    assert 8 <= len(pasta["steps"]) <= 12
    sweat, brown = recipes.step("pasta_pomodoro", "sweat_onion"), recipes.step("curry_onion", "brown_onion")
    assert set(sweat["skills"]) == set(brown["skills"])  # the same skills transfer...
    assert sweat["target"]["color"] < brown["target"]["color"]  # ...towards different goals
    assert (sweat["salt"], brown["salt"]) == ("early", "late")


def test_onion_model_outcome_depends_on_action():
    mid = onion.Onion(color=0.32, moisture=0.45, heat=7)
    after = {a: onion.simulate(onion.apply_action(mid, a), 120).color
             for a in ("lower_heat", "continue_observe", "raise_heat")}
    assert after["lower_heat"] < after["continue_observe"] < after["raise_heat"]
    wet = onion.Onion(color=0.3, moisture=0.7, heat=6)
    salted_early = onion.simulate(onion.apply_action(wet, "add_salt_now"), 300)
    assert salted_early.color < onion.simulate(wet, 300).color, "early salt delays browning"


def test_reducer_keeps_provenance_conflicts_and_versions():
    s0 = state.initial_state("pasta_pomodoro")
    s1 = state.apply_event(s0, ev(1, "camera", 10, step_id="sweat_onion", onion_color=0.3))
    s2 = state.apply_event(s1, ev(2, "transcript", 12, heat_level=6))
    assert s2.facts["onion_color"].status == FactStatus.observed
    assert s2.facts["heat_level"].status == FactStatus.self_reported
    s3 = state.apply_event(s2, ev(3, "manual", 15, heat_level=9))  # disagrees within the window
    assert s3.facts["heat_level"].status == FactStatus.conflict
    assert s3.facts["heat_level"].alt == 6 and state.known(s3, "heat_level") is None
    assert s3.version == 3 and state.is_stale(2, s3) and not state.is_stale(3, s3)
    assert s0.version == 0 and not s0.facts, "the reducer never mutates its input"


def test_only_observed_outcomes_raise_skill_levels():
    b = belief.new_beliefs()
    for kind in ("prompt_given", "prompt_acknowledged", "self_reported_done", "not_followed"):
        belief.add_evidence(b, Evidence(kind=kind, skill_id="heat_control",
                                        recipe_id="pasta_pomodoro", step_id="sweat_onion", ts=1))
    assert b["heat_control"].level == SkillLevel.unknown and len(b["heat_control"].evidence) == 4
    for kind, level in ((EvidenceKind.observed_guided_success, SkillLevel.guided_success),
                        (EvidenceKind.observed_independent_success, SkillLevel.independent_success),
                        (EvidenceKind.observed_failure, SkillLevel.guided_success)):
        belief.add_evidence(b, Evidence(kind=kind, skill_id="heat_control",
                                        recipe_id="pasta_pomodoro", step_id="sweat_onion", ts=2))
        assert b["heat_control"].level == level


def test_candidates_are_feasible_and_include_doing_nothing():
    s = state.apply_event(state.initial_state("pasta_pomodoro"),
                          ev(1, "camera", 5, step_id="sweat_onion", onion_color=0.2, moisture=0.8))
    by_id = {c.candidate_id: c for c in candidates.all_candidates(s)}
    assert not by_id["recut_onion"].feasible and "下次" in by_id["recut_onion"].reason_infeasible
    picked = [c.candidate_id for c in candidates.generate(s)]
    assert 2 <= len(picked) <= 3 and "continue_observe" in picked
    assert "ask_heat_level" in picked, "unknown heat should be askable"
    curry = state.apply_event(state.initial_state("curry_onion"),
                              ev(2, "camera", 5, step_id="brown_onion", onion_color=0.3, heat_level=6))
    assert not {c.candidate_id: c for c in candidates.all_candidates(curry)}["add_salt_now"].feasible


def sweat(**facts):
    """Pasta at the sweat-the-onion step, with these camera facts."""
    return state.apply_event(state.initial_state("pasta_pomodoro"),
                             ev(1, "camera", 10, step_id="sweat_onion", **facts))


def decide(s, beliefs=None):
    beliefs = beliefs or belief.new_beliefs()
    rule = policy.rule_decision(s)
    if rule:
        return rule
    cands = candidates.generate(s)
    return policy.choose(cands, MockProvider().compare(s, beliefs, cands), beliefs).candidate_id


def test_world_model_compares_every_candidate_and_caches():
    s = sweat(onion_color=0.32, moisture=0.45, heat_level=7.0, salted=True)
    cands = candidates.generate(s)
    wm = WorldModel(MockProvider())
    preds, source = wm.compare(s, belief.new_beliefs(), cands)
    assert source == "model" and [p.candidate_id for p in preds] == [c.candidate_id for c in cands]
    assert len({p.target_gap for p in preds}) == len(preds), "different moves, different futures"
    assert wm.compare(s, belief.new_beliefs(), cands)[1] == "cache"
    darker = state.apply_event(s, ev(2, "camera", 20, onion_color=0.5))
    assert wm.compare(darker, belief.new_beliefs(), candidates.generate(darker))[1] == "model"


def test_policy_rule_then_ask_then_teach_or_stay_quiet():
    assert policy.rule_decision(sweat(smoke=True)) == "lower_heat"
    assert decide(sweat(onion_color=0.35, moisture=0.5)) == "ask_heat_level", "unknown heat that matters"
    early = sweat(onion_color=0.1, moisture=0.9, heat_level=4.0, salted=False)
    assert decide(early) == "add_salt_now", "novice: teach salting at the right moment"
    seasoned = belief.new_beliefs()
    belief.add_evidence(seasoned, Evidence(kind="observed_independent_success", skill_id="salt_timing",
                                           recipe_id="pasta_pomodoro", step_id="sweat_onion", ts=0))
    assert decide(early, seasoned) == "continue_observe", "someone who salts unprompted is left alone"
    fine = sweat(onion_color=0.15, moisture=0.85, heat_level=4.0, salted=True)
    assert decide(fine) == "continue_observe", "nothing to fix, nothing to teach: stay quiet"


def pasta_then_curry(memory):
    s = Session("learner-1", "pasta_pomodoro", MockProvider(), memory=memory)
    first = s.observe(ev(1, "camera", 10, step_id="sweat_onion", onion_color=0.1, moisture=0.9,
                         heat_level=4.0, salted=False))
    s.observe(ev(2, "manual", 300, step_id="add_garlic", step_done=True, outcome="good",
                 onion_color=0.32, moisture=0.55, salted=True))
    s.observe(ev(3, "manual", 360, step_id="add_tomatoes", step_done=True, outcome="good"))
    s.switch_recipe("curry_onion", 400)
    curry = s.observe(ev(4, "camera", 1300, step_id="brown_onion", onion_color=0.72, moisture=0.3,
                         heat_level=3.0, salted=True))
    return s, first, curry


def test_memory_from_pasta_changes_coaching_in_curry():
    s, first, curry = pasta_then_curry(memory=True)
    assert first.candidate_id == "add_salt_now" and first.speak
    assert s.beliefs["salt_timing"].level.value == "guided_success", "prompted, then done"
    assert s.beliefs["step_judgment"].level.value == "independent_success", "moved on unprompted"
    assert {e.recipe_id for e in s.beliefs["step_judgment"].evidence} == {"pasta_pomodoro"}
    assert not curry.speak, "seasoned learner at the browning target: no interruption"
    _, _, fresh = pasta_then_curry(memory=False)
    assert fresh.candidate_id == "advance_step" and fresh.speak, "ablation A1 (no memory) teaches it"


def test_ignored_advice_is_recorded_but_never_counts_as_success():
    s = Session("learner-2", "pasta_pomodoro", MockProvider())
    d = s.observe(ev(1, "camera", 10, step_id="sweat_onion", smoke=True, heat_level=8.0))
    assert (d.source, d.candidate_id, d.speak) == ("rule", "lower_heat", True)
    assert not s.observe(ev(2, "camera", 25, smoke=True)).speak, "same advice 15 s later stays muted"
    s.respond(LearnerResponse(decision_id=d.decision_id, kind="not_followed", ts=30))
    hc = s.beliefs["heat_control"]
    assert hc.level.value == "unknown" and hc.evidence[-1].kind.value == "not_followed"
    s.respond(LearnerResponse(decision_id=d.decision_id, kind="observed_success", ts=40))
    assert s.beliefs["heat_control"].level.value == "guided_success"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} tests passed")
