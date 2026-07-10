"""Base class every business rule extends.

A rule is a small, single-responsibility, side-effect-free object:
``evaluate(context) → RuleResult``. Identity (name/category/priority) lives
on the class; the base provides result constructors so rule bodies stay
declarative and every result is uniformly shaped.

Priorities: lower numbers run earlier. Bands used by the platform:
    10–19 validation · 20–29 compliance · 30–39 risk · 40–69 domain
    70–79 eligibility (chaining) · 90–99 recommendation (chaining)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity, RuleStatus


class BaseRule(ABC):
    """One evaluable business rule."""

    #: Unique, stable rule identifier (shown in traces and reports).
    name: str = "base_rule"
    #: Rule family — used for scoped runs and chaining lookups.
    category: str = "general"
    #: Execution order — lower runs earlier (see module docstring bands).
    priority: int = 100
    #: One-line business meaning, surfaced by documentation endpoints.
    description: str = ""

    @abstractmethod
    def evaluate(self, context: RuleContext) -> RuleResult:
        """Evaluate the rule against the context. Must not mutate it."""

    # ------------------------------------------------------------------
    # Result constructors (uniform shape, minimal ceremony in rule bodies)
    # ------------------------------------------------------------------
    def _result(self, status: RuleStatus, severity: RuleSeverity, reason: str,
                evidence: dict[str, Any] | None,
                recommendation: str) -> RuleResult:
        return RuleResult(
            rule_name=self.name, category=self.category, status=status,
            severity=severity, reason=reason, evidence=evidence or {},
            recommendation=recommendation, priority=self.priority,
        )

    def passed(self, reason: str, evidence: dict[str, Any] | None = None,
               recommendation: str = "",
               severity: RuleSeverity = RuleSeverity.INFO) -> RuleResult:
        return self._result(RuleStatus.PASS, severity, reason, evidence,
                            recommendation)

    def failed(self, reason: str, evidence: dict[str, Any] | None = None,
               recommendation: str = "",
               severity: RuleSeverity = RuleSeverity.HIGH) -> RuleResult:
        return self._result(RuleStatus.FAIL, severity, reason, evidence,
                            recommendation)

    def warning(self, reason: str, evidence: dict[str, Any] | None = None,
                recommendation: str = "",
                severity: RuleSeverity = RuleSeverity.MEDIUM) -> RuleResult:
        return self._result(RuleStatus.WARNING, severity, reason, evidence,
                            recommendation)

    def info(self, reason: str, evidence: dict[str, Any] | None = None,
             recommendation: str = "") -> RuleResult:
        return self._result(RuleStatus.INFO, RuleSeverity.INFO, reason,
                            evidence, recommendation)
