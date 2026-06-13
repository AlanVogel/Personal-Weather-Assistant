"""A small, dependency-free evaluator for recommendation output quality."""

from dataclasses import dataclass

from app.recommendations.models import DailyRecommendation

from .scenarios import WeatherScenario


@dataclass(frozen=True)
class EvalResult:
    """Outcome of scoring one recommendation against one scenario."""

    scenario: str
    passed: bool
    matched_groups: int
    total_groups: int
    missing: list[str]

    @property
    def score(self) -> float:
        """Fraction of expected keyword groups that were satisfied (0.0–1.0)."""
        if self.total_groups == 0:
            return 1.0
        return self.matched_groups / self.total_groups


def flatten_recommendation_text(rec: DailyRecommendation) -> str:
    """Collect all human-readable text from a recommendation into one string."""
    parts: list[str] = [rec.summary, rec.clothing.reasoning, rec.activities.reasoning]
    parts.extend(rec.clothing.items)
    parts.extend(rec.activities.suggested)
    parts.extend(rec.activities.avoid)
    parts.extend(tip.tip for tip in rec.health_tips)
    if rec.weekly_advice:
        parts.append(rec.weekly_advice)
    return " ".join(parts).lower()


def evaluate(rec: DailyRecommendation, scenario: WeatherScenario) -> EvalResult:
    """Score a recommendation: every expected keyword group must be hit once."""
    haystack = flatten_recommendation_text(rec)

    matched = 0
    missing: list[str] = []
    for group in scenario.expected_keyword_groups:
        if any(keyword.lower() in haystack for keyword in group):
            matched += 1
        else:
            missing.append(" | ".join(group))

    total = len(scenario.expected_keyword_groups)
    return EvalResult(
        scenario=scenario.name,
        passed=matched == total,
        matched_groups=matched,
        total_groups=total,
        missing=missing,
    )
