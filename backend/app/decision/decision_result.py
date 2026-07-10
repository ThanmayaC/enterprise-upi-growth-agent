"""Decision result — the platform's final, fully-explainable answer shape.

Combines the ML prediction(s), the analytics facts, and the complete rule
report into one auditable object. A decision is never a bare label: it
always carries confidence, the rule trail, the predictions and analytics
it used, business reasons, a recommended action, and supporting evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DecisionResult:
    """The final outcome of one decision evaluation."""

    subject: dict[str, Any]                 # what/who was decided on
    question: str                           # the business question answered
    decision: str                           # final verdict label
    confidence: float                       # combined ML × rules confidence
    rule_results: list[dict[str, Any]]      # every RuleResult (dict form)
    trace: list[dict[str, Any]]             # ordered decision trace
    predictions_used: dict[str, Any]        # ML records that informed this
    analytics_used: dict[str, Any]          # analytics facts that informed this
    business_reasons: list[str]             # human-readable reasoning
    recommended_action: str                 # single concrete next step
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "question": self.question,
            "decision": self.decision,
            "confidence": self.confidence,
            "rule_results": self.rule_results,
            "trace": self.trace,
            "predictions_used": self.predictions_used,
            "analytics_used": self.analytics_used,
            "business_reasons": self.business_reasons,
            "recommended_action": self.recommended_action,
            "evidence": self.evidence,
        }
