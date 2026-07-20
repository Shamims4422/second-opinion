from dataclasses import dataclass

SCORING_VERSION = "v1"

# Component weights; see PLAN.md section 8.
WEIGHT_SUCCESS = 0.45
WEIGHT_SIMILARITY = 0.25
WEIGHT_EVIDENCE = 0.20
WEIGHT_TOOL = 0.10

# Applied when a tool (or the whole system) has no recorded history yet.
NEUTRAL_RELIABILITY = 0.5
COLD_START_CONFIDENCE = 0.5
EVIDENCE_SATURATION = 10


@dataclass(frozen=True)
class Evidence:
    """A retrieved similar experience that has a recorded outcome."""

    similarity: float
    was_successful: bool


@dataclass(frozen=True)
class ScoringResult:
    confidence: float
    decision: str
    reason: str
    evidence_count: int
    scoring_version: str


class ScoringService:
    def __init__(self, approve_threshold: float = 0.75, block_threshold: float = 0.45) -> None:
        self.approve_threshold = approve_threshold
        self.block_threshold = block_threshold

    @staticmethod
    def weighted_success_rate(evidence: list[Evidence]) -> float:
        total_weight = sum(e.similarity for e in evidence)
        if total_weight <= 0:
            return 0.0
        return sum(e.similarity * (1.0 if e.was_successful else 0.0) for e in evidence) / (
            total_weight
        )

    @staticmethod
    def average_similarity(evidence: list[Evidence]) -> float:
        if not evidence:
            return 0.0
        return sum(e.similarity for e in evidence) / len(evidence)

    @staticmethod
    def evidence_strength(evidence_count: int) -> float:
        return min(evidence_count / EVIDENCE_SATURATION, 1.0)

    def decide(self, confidence: float) -> str:
        if confidence >= self.approve_threshold:
            return "approve"
        if confidence >= self.block_threshold:
            return "revise"
        return "block"

    def score(
        self,
        evidence: list[Evidence],
        tool_reliability: float | None = None,
        tool_name: str | None = None,
    ) -> ScoringResult:
        if not evidence:
            return ScoringResult(
                confidence=COLD_START_CONFIDENCE,
                decision=self.decide(COLD_START_CONFIDENCE),
                reason="Not enough previous experience is available.",
                evidence_count=0,
                scoring_version=SCORING_VERSION,
            )

        success_rate = self.weighted_success_rate(evidence)
        avg_similarity = self.average_similarity(evidence)
        strength = self.evidence_strength(len(evidence))
        reliability = NEUTRAL_RELIABILITY if tool_reliability is None else tool_reliability

        confidence = (
            WEIGHT_SUCCESS * success_rate
            + WEIGHT_SIMILARITY * avg_similarity
            + WEIGHT_EVIDENCE * strength
            + WEIGHT_TOOL * reliability
        )
        confidence = round(max(0.0, min(1.0, confidence)), 4)

        successes = sum(1 for e in evidence if e.was_successful)
        failures = len(evidence) - successes
        reason = (
            f"{len(evidence)} similar past action(s) were found "
            f"(average similarity {avg_similarity:.2f}); "
            f"{successes} succeeded and {failures} failed."
        )
        if tool_reliability is not None and tool_name:
            reason += (
                f" Historically, '{tool_name}' actions succeed "
                f"{tool_reliability:.0%} of the time."
            )

        return ScoringResult(
            confidence=confidence,
            decision=self.decide(confidence),
            reason=reason,
            evidence_count=len(evidence),
            scoring_version=SCORING_VERSION,
        )
