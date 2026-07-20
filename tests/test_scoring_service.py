import pytest

from app.services.scoring_service import Evidence, ScoringService


def make_evidence(pairs: list[tuple[float, bool]]) -> list[Evidence]:
    return [Evidence(similarity=s, was_successful=ok) for s, ok in pairs]


def test_all_successes_scores_high() -> None:
    evidence = make_evidence([(0.9, True)] * 5)
    result = ScoringService().score(evidence, tool_reliability=0.9, tool_name="browser")
    assert result.decision == "approve"
    assert result.confidence > 0.75
    assert result.evidence_count == 5


def test_all_failures_scores_low() -> None:
    evidence = make_evidence([(0.9, False)] * 5)
    result = ScoringService().score(evidence, tool_reliability=0.1, tool_name="shell")
    assert result.decision == "block"
    assert result.confidence < 0.45


def test_mixed_outcomes_land_in_the_middle() -> None:
    evidence = make_evidence([(0.8, True), (0.8, False), (0.8, True), (0.8, False)])
    result = ScoringService().score(evidence, tool_reliability=0.5)
    assert 0.45 <= result.confidence < 0.75
    assert result.decision == "revise"


def test_cold_start_returns_neutral_revise() -> None:
    result = ScoringService().score([])
    assert result.confidence == 0.5
    assert result.decision == "revise"
    assert result.reason == "Not enough previous experience is available."
    assert result.evidence_count == 0


def test_low_similarity_reduces_confidence() -> None:
    high_sim = ScoringService().score(make_evidence([(0.95, True)] * 3))
    low_sim = ScoringService().score(make_evidence([(0.35, True)] * 3))
    assert low_sim.confidence < high_sim.confidence


def test_similar_failure_outweighs_less_similar_successes() -> None:
    # One highly similar failure among several weaker successes drags the
    # weighted success rate well below the raw success ratio (3/4 = 0.75).
    evidence = make_evidence([(0.98, False), (0.4, True), (0.4, True), (0.4, True)])
    result = ScoringService().score(evidence)
    assert ScoringService.weighted_success_rate(evidence) < 0.75
    assert result.confidence < ScoringService().score(make_evidence([(0.4, True)] * 3)).confidence


def test_confidence_stays_within_bounds() -> None:
    best = ScoringService().score(make_evidence([(1.0, True)] * 20), tool_reliability=1.0)
    worst = ScoringService().score(make_evidence([(1.0, False)] * 20), tool_reliability=0.0)
    assert 0.0 <= worst.confidence <= 1.0
    assert 0.0 <= best.confidence <= 1.0


def test_weighted_success_rate_weights_by_similarity() -> None:
    evidence = make_evidence([(0.9, True), (0.1, False)])
    rate = ScoringService.weighted_success_rate(evidence)
    assert rate == pytest.approx(0.9)


def test_evidence_strength_saturates_at_ten() -> None:
    assert ScoringService.evidence_strength(0) == 0.0
    assert ScoringService.evidence_strength(5) == 0.5
    assert ScoringService.evidence_strength(10) == 1.0
    assert ScoringService.evidence_strength(50) == 1.0


def test_decision_thresholds() -> None:
    service = ScoringService(approve_threshold=0.75, block_threshold=0.45)
    assert service.decide(0.75) == "approve"
    assert service.decide(0.7499) == "revise"
    assert service.decide(0.45) == "revise"
    assert service.decide(0.4499) == "block"


def test_missing_tool_reliability_uses_neutral_value() -> None:
    evidence = make_evidence([(0.8, True)] * 4)
    with_neutral = ScoringService().score(evidence, tool_reliability=None)
    with_half = ScoringService().score(evidence, tool_reliability=0.5, tool_name="browser")
    assert with_neutral.confidence == with_half.confidence


def test_reason_mentions_evidence_and_tool_history() -> None:
    evidence = make_evidence([(0.8, True), (0.8, False)])
    result = ScoringService().score(evidence, tool_reliability=0.72, tool_name="browser")
    assert "2 similar past action(s)" in result.reason
    assert "1 succeeded and 1 failed" in result.reason
    assert "'browser' actions succeed 72%" in result.reason
