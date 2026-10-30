"""Checks for the live cooking coach. Run: python3 test_livecoach.py"""
from livecoach import belief, candidates, onion, recipes, state
from livecoach.schema import Evidence, EvidenceKind, FactStatus, ObservationEvent, SkillLevel


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


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} tests passed")
