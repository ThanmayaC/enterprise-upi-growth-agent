"""Rule outcome contract — every rule returns exactly this shape.

A :class:`RuleResult` is the atomic unit of decision evidence: rule name,
status (PASS / FAIL / WARNING / INFO), severity, a human-readable reason,
the numeric/config evidence behind it, and a recommendation. Results are
JSON-ready so the Decision layer, future AI Copilot, and Report Generator
can consume them without translation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleStatus(str, Enum):
    """Terminal status of one rule evaluation."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    INFO = "INFO"


class RuleSeverity(str, Enum):
    """Business weight of a rule outcome (drives decision mapping)."""

    CRITICAL = "CRITICAL"   # failing blocks the decision outright
    HIGH = "HIGH"           # failing normally blocks, may force review
    MEDIUM = "MEDIUM"       # failing degrades the decision / adds conditions
    LOW = "LOW"             # advisory
    INFO = "INFO"           # informational only


@dataclass
class RuleResult:
    """The complete, explainable outcome of a single rule."""

    rule_name: str
    category: str
    status: RuleStatus
    severity: RuleSeverity
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    priority: int = 100

    @property
    def passed(self) -> bool:
        return self.status is RuleStatus.PASS

    @property
    def failed(self) -> bool:
        return self.status is RuleStatus.FAIL

    @property
    def blocking(self) -> bool:
        """A failure severe enough to block an approval decision."""

        return self.failed and self.severity in (
            RuleSeverity.CRITICAL, RuleSeverity.HIGH
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "category": self.category,
            "status": self.status.value,
            "severity": self.severity.value,
            "reason": self.reason,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "priority": self.priority,
        }
