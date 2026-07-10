"""Decision engine — combines rule reports and ML confidence into verdicts.

Decision mapping (uniform across every use case):

    blocking failure (CRITICAL/HIGH FAIL) → the *reject* label
    any other failure                     → the *review* label
    warnings only                         → the *conditional* label
    all clear                             → the *approve* label

Confidence = mean ML confidence × rule pass-ratio: a decision is only as
strong as both its statistical evidence and its rule agreement. Business
reasons and the recommended action are lifted from the rule results, so
the final answer is always explainable end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.decision.decision_context import rule_evidence, used_predictions
from app.decision.decision_result import DecisionResult
from app.rules.rule_context import RuleContext
from app.rules.rule_engine import RuleReport
from app.rules.rule_result import RuleStatus


@dataclass(frozen=True)
class DecisionLabels:
    """Verdict vocabulary for one decision use case."""

    approve: str
    conditional: str
    review: str
    reject: str


class DecisionEngine:
    """Turn (context, rule report) into a final, explainable decision."""

    def decide(
        self,
        *,
        subject: dict[str, Any],
        question: str,
        context: RuleContext,
        report: RuleReport,
        labels: DecisionLabels,
        decision_override: str | None = None,
    ) -> DecisionResult:
        """Assemble the final decision from an evaluated rule report.

        ``decision_override`` lets score-style use cases (e.g. merchant
        priority) replace the eligibility vocabulary with a computed label
        while keeping the whole evidence structure identical.
        """

        if report.blocking_failures:
            decision = labels.reject
        elif not report.passed:
            decision = labels.review
        elif report.summary.get(RuleStatus.WARNING.value, 0) > 0:
            decision = labels.conditional
        else:
            decision = labels.approve
        if decision_override is not None:
            decision = decision_override

        confidences = [
            float(rec["confidence"])
            for rec in context.predictions.values()
            if rec.get("confidence") is not None
        ]
        ml_confidence = (sum(confidences) / len(confidences)) if confidences else 0.5
        confidence = round(ml_confidence * report.pass_ratio, 4)

        business_reasons = [
            f"[{r.status.value}] {r.reason}"
            for r in report.results
            if r.status in (RuleStatus.FAIL, RuleStatus.WARNING)
            or r.category in ("eligibility", "recommendation")
        ]
        recommended = next(
            (r.recommendation for r in reversed(report.results)
             if r.category == "recommendation" and r.recommendation),
            next((r.recommendation for r in report.results
                  if r.failed and r.recommendation), "PROCEED"),
        )

        return DecisionResult(
            subject=subject,
            question=question,
            decision=decision,
            confidence=confidence,
            rule_results=[r.to_dict() for r in report.results],
            trace=report.trace,
            predictions_used=used_predictions(context),
            analytics_used=context.analytics,
            business_reasons=business_reasons,
            recommended_action=recommended,
            evidence={
                "rule_summary": report.summary,
                "rule_pass_ratio": round(report.pass_ratio, 4),
                "ml_confidence": round(ml_confidence, 4),
                "config_snapshot": context.config.to_dict(),
                "rule_evidence": rule_evidence(report.results),
            },
        )
