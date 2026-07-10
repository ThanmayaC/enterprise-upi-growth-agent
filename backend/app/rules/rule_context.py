"""Rule evaluation context — everything a rule may look at, injected once.

The context is assembled by the Decision layer from Analytics results, ML
predictions, NPCI configuration, and entity data. Rules read *only* the
context; they never query the database, call services, or import ML code.
``prior_results`` enables rule chaining: later (higher-priority-number)
rules can reason over the outcomes of earlier ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.rules.npci_config import NpciRuleConfig
from app.rules.rule_result import RuleResult


@dataclass
class RuleContext:
    """Read-only facts for one evaluation run (one subject, one question)."""

    config: NpciRuleConfig = field(default_factory=NpciRuleConfig)
    #: ML predictions keyed by a stable name (e.g. ``merchant_growth``,
    #: ``merchant_autopay``) — full prediction records incl. confidence,
    #: probabilities, important features, model, version, reason.
    predictions: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Analytics facts keyed by a stable name (e.g. ``merchant_traffic``).
    analytics: dict[str, Any] = field(default_factory=dict)
    #: Entity data (already loaded by the Decision layer — no SQL here).
    merchant: dict[str, Any] | None = None
    customer: dict[str, Any] | None = None
    transaction: dict[str, Any] | None = None
    #: Results appended by the engine as rules execute (chaining substrate).
    prior_results: list[RuleResult] = field(default_factory=list)
    #: Free-form extras (e.g. attempt counters) supplied by the caller.
    extras: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience accessors (keep rule bodies declarative)
    # ------------------------------------------------------------------
    def prediction(self, key: str) -> dict[str, Any]:
        """A named ML prediction record ({} when absent)."""

        return self.predictions.get(key) or {}

    def analytic(self, key: str) -> Any:
        """A named analytics fact (None when absent)."""

        return self.analytics.get(key)

    def prior(self, *, category: str | None = None,
              rule_name: str | None = None) -> list[RuleResult]:
        """Earlier results, optionally filtered (rule chaining)."""

        out = self.prior_results
        if category is not None:
            out = [r for r in out if r.category == category]
        if rule_name is not None:
            out = [r for r in out if r.rule_name == rule_name]
        return list(out)
