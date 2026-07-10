"""Eligibility rules (priority 70–79) — chained verdicts.

These run *after* the domain rules and reason over ``context.prior_results``
(rule chaining): an eligibility verdict is the aggregation of its
constituent checks, so the full evidence trail stays intact.
"""

from __future__ import annotations

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity, RuleStatus


def _chain_summary(results: list) -> dict[str, list[str]]:
    """Names of failed/warned rules for chained evidence."""

    return {
        "failed_rules": [r.rule_name for r in results if r.failed],
        "warned_rules": [r.rule_name for r in results
                         if r.status is RuleStatus.WARNING],
        "passed_rules": [r.rule_name for r in results if r.passed],
    }


class AutopayEligibilityRule(BaseRule):
    """Final Autopay verdict: chains autopay + compliance results.

    Eligible ⇔ no failure among the autopay domain checks (prediction,
    recurring usage, amount limit) and no blocking compliance failure.
    """

    name = "autopay_eligibility"
    category = "eligibility"
    priority = 70
    description = "Aggregated Autopay eligibility from prior rule outcomes."

    def evaluate(self, context: RuleContext) -> RuleResult:
        considered = (context.prior(category="autopay")
                      + context.prior(category="compliance"))
        if not considered:
            return self.warning(
                "No autopay/compliance results to chain — verdict unavailable.")
        evidence = _chain_summary(considered)
        failures = [r for r in considered if r.failed]
        if failures:
            worst = max(failures, key=lambda r: r.severity is RuleSeverity.CRITICAL)
            return self.failed(
                f"Not eligible for Autopay — {len(failures)} check(s) failed "
                f"(e.g. {worst.rule_name}: {worst.reason})",
                severity=RuleSeverity.HIGH, evidence=evidence,
                recommendation="Address the failed checks before re-evaluation.",
            )
        warnings = evidence["warned_rules"]
        if warnings:
            return self.passed(
                f"Eligible for Autopay with {len(warnings)} advisory "
                f"condition(s): {', '.join(warnings)}.",
                evidence=evidence, severity=RuleSeverity.LOW,
                recommendation="Proceed; monitor the advisory conditions.",
            )
        return self.passed("Eligible for Autopay — all checks passed.",
                           evidence=evidence,
                           recommendation="Proceed with mandate onboarding.")


class MerchantProgramEligibilityRule(BaseRule):
    """Growth-program eligibility chained over the merchant checks."""

    name = "merchant_program_eligibility"
    category = "eligibility"
    priority = 72
    description = "Aggregated merchant program eligibility from prior outcomes."

    def evaluate(self, context: RuleContext) -> RuleResult:
        considered = context.prior(category="merchant")
        if not considered:
            return self.warning("No merchant rule results to chain.")
        evidence = _chain_summary(considered)
        failures = [r for r in considered if r.failed]
        if failures:
            return self.failed(
                f"Not eligible for the growth program — failed: "
                f"{', '.join(r.rule_name for r in failures)}.",
                severity=RuleSeverity.MEDIUM, evidence=evidence,
                recommendation="Remediate the failed checks first.",
            )
        return self.passed("Eligible for the merchant growth program.",
                           evidence=evidence)


class CustomerProgramEligibilityRule(BaseRule):
    """Engagement-program eligibility chained over the customer checks."""

    name = "customer_program_eligibility"
    category = "eligibility"
    priority = 74
    description = "Aggregated customer program eligibility from prior outcomes."

    def evaluate(self, context: RuleContext) -> RuleResult:
        considered = context.prior(category="customer")
        if not considered:
            return self.warning("No customer rule results to chain.")
        evidence = _chain_summary(considered)
        failures = [r for r in considered if r.failed]
        if failures:
            return self.failed(
                f"Not eligible for standard programs — failed: "
                f"{', '.join(r.rule_name for r in failures)}.",
                severity=RuleSeverity.MEDIUM, evidence=evidence,
                recommendation="Route to the remediation/retention track instead.",
            )
        return self.passed("Eligible for customer engagement programs.",
                           evidence=evidence)
