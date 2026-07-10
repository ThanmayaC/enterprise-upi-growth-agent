"""Enterprise rule engine: registration, priorities, chaining, decision trace.

The engine owns a registry of :class:`BaseRule` instances. An evaluation
run executes the selected rules in priority order (lower number first,
name as tie-break), appends each result to ``context.prior_results`` so
later rules can chain on earlier outcomes, and records an ordered decision
trace. A misbehaving rule never aborts the run — it is captured as a FAIL
result with the exception as evidence (the trace stays complete).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity, RuleStatus


@dataclass
class RuleReport:
    """The complete outcome of one engine run."""

    results: list[RuleResult]
    trace: list[dict[str, Any]]           # ordered decision trace
    summary: dict[str, int]               # counts per status
    blocking_failures: list[RuleResult]   # FAILs with CRITICAL/HIGH severity

    @property
    def passed(self) -> bool:
        """True when nothing failed (warnings/info allowed)."""

        return self.summary.get(RuleStatus.FAIL.value, 0) == 0

    @property
    def pass_ratio(self) -> float:
        """Share of PASS among decisive (PASS/FAIL) results — in [0, 1]."""

        decisive = [r for r in self.results
                    if r.status in (RuleStatus.PASS, RuleStatus.FAIL)]
        if not decisive:
            return 1.0
        return sum(1 for r in decisive if r.passed) / len(decisive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "trace": self.trace,
            "summary": self.summary,
            "passed": self.passed,
            "pass_ratio": round(self.pass_ratio, 4),
        }


class RuleEngine:
    """Priority-ordered registry and executor for business rules."""

    def __init__(self) -> None:
        self._rules: dict[str, BaseRule] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, rule: BaseRule) -> "RuleEngine":
        """Register one rule (name must be unique)."""

        if rule.name in self._rules:
            raise ValueError(f"rule {rule.name!r} is already registered")
        self._rules[rule.name] = rule
        return self

    def register_all(self, rules: Iterable[BaseRule]) -> "RuleEngine":
        for rule in rules:
            self.register(rule)
        return self

    def rules(self, categories: Iterable[str] | None = None) -> list[BaseRule]:
        """Registered rules in execution order, optionally per category."""

        selected = self._rules.values()
        if categories is not None:
            wanted = set(categories)
            selected = [r for r in selected if r.category in wanted]
        return sorted(selected, key=lambda r: (r.priority, r.name))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def evaluate(self, context: RuleContext,
                 categories: Iterable[str] | None = None) -> RuleReport:
        """Run the selected rules in priority order against the context."""

        results: list[RuleResult] = []
        trace: list[dict[str, Any]] = []
        summary: dict[str, int] = {s.value: 0 for s in RuleStatus}

        for position, rule in enumerate(self.rules(categories), start=1):
            started = time.perf_counter()
            try:
                result = rule.evaluate(context)
            except Exception as exc:  # a broken rule must not kill the run
                result = RuleResult(
                    rule_name=rule.name, category=rule.category,
                    status=RuleStatus.FAIL, severity=RuleSeverity.HIGH,
                    reason=f"rule raised {type(exc).__name__}: {exc}",
                    evidence={"exception": str(exc)},
                    recommendation="Investigate rule implementation/context.",
                    priority=rule.priority,
                )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

            results.append(result)
            context.prior_results.append(result)  # chaining substrate
            summary[result.status.value] += 1
            trace.append({
                "position": position,
                "rule": rule.name,
                "category": rule.category,
                "priority": rule.priority,
                "status": result.status.value,
                "severity": result.severity.value,
                "elapsed_ms": elapsed_ms,
            })

        blocking = [r for r in results if r.blocking]
        return RuleReport(results=results, trace=trace, summary=summary,
                          blocking_failures=blocking)
