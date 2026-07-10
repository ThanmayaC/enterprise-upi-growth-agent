"""Merchant rules (priority 40–49) — growth outlook, reliability, priority.

``MerchantPriorityScoreRule`` implements the specified composite:
growth prediction + success rate + scale + business category → a 0–100
priority score with a config-driven tier, carried as evidence for the
Decision layer and the recommendation rules.
"""

from __future__ import annotations

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity


class MerchantGrowthOutlookRule(BaseRule):
    """The ML growth outlook should not be 'Declining'."""

    name = "merchant_growth_outlook"
    category = "merchant"
    priority = 40
    description = "Predicted growth category is Stable or better."

    def evaluate(self, context: RuleContext) -> RuleResult:
        record = context.prediction("merchant_growth")
        category = record.get("growth_category")
        pct = record.get("expected_growth_pct")
        if category is None:
            return self.warning("No growth prediction in context.")
        evidence = {"growth_category": category,
                    "expected_growth_pct": pct,
                    "model": record.get("model"),
                    "version": record.get("version")}
        if category == "Declining":
            return self.warning(
                f"Growth outlook is Declining ({pct:+.1f}% expected).",
                evidence=evidence,
                recommendation="Prioritize a retention/turnaround program.",
            )
        return self.passed(
            f"Growth outlook is {category} ({pct:+.1f}% expected).",
            evidence=evidence,
        )


class MerchantSuccessRateRule(BaseRule):
    """Observed success rate must clear the configured program bar."""

    name = "merchant_success_rate"
    category = "merchant"
    priority = 42
    description = "Merchant success rate meets the eligibility minimum."

    def evaluate(self, context: RuleContext) -> RuleResult:
        merchant = context.merchant or {}
        rate = merchant.get("success_rate")
        if rate is None:
            return self.warning("No success-rate analytics for the merchant.")
        minimum = context.config.merchant_min_success_rate
        rate = float(rate)
        if rate < minimum:
            return self.failed(
                f"Success rate {rate:.1f}% is below the program minimum "
                f"{minimum:.0f}%.",
                severity=RuleSeverity.MEDIUM,
                evidence={"success_rate_pct": rate, "minimum_pct": minimum},
                recommendation="Remediate reliability before program enrollment.",
            )
        return self.passed(
            f"Success rate {rate:.1f}% meets the {minimum:.0f}% minimum.",
            evidence={"success_rate_pct": rate, "minimum_pct": minimum},
        )


class MerchantScaleRule(BaseRule):
    """The merchant needs a minimum activity base for program decisions."""

    name = "merchant_scale"
    category = "merchant"
    priority = 44
    description = "Merchant transaction volume meets the observation minimum."

    def evaluate(self, context: RuleContext) -> RuleResult:
        merchant = context.merchant or {}
        txns = merchant.get("total_transactions")
        if txns is None:
            return self.warning("No traffic analytics for the merchant.")
        minimum = context.config.merchant_min_period_transactions
        txns = int(txns)
        if txns < minimum:
            return self.warning(
                f"Only {txns} transactions in the window (minimum {minimum}).",
                evidence={"total_transactions": txns, "minimum": minimum},
                recommendation="Re-evaluate after more activity accrues.",
            )
        return self.passed(
            f"{txns:,d} transactions in the window (minimum {minimum}).",
            evidence={"total_transactions": txns, "minimum": minimum},
        )


class MerchantPriorityScoreRule(BaseRule):
    """Composite 0–100 priority score with a config-driven tier."""

    name = "merchant_priority_score"
    category = "merchant"
    priority = 46
    description = ("Weighted priority score from growth prediction, success "
                   "rate, scale, and category autopay affinity.")

    def evaluate(self, context: RuleContext) -> RuleResult:
        cfg = context.config
        merchant = context.merchant or {}
        growth = context.prediction("merchant_growth")

        # Component scores, each normalized to 0–100.
        growth_pct = float(growth.get("expected_growth_pct") or 0.0)
        growth_score = max(0.0, min(100.0, (growth_pct + 100.0) / 3.0))
        success_score = float(merchant.get("success_rate") or 0.0)
        volume = float(merchant.get("total_transactions") or 0.0)
        scale_score = max(0.0, min(100.0, 100.0 * volume / 5_000.0))
        category_score = 100.0 * float(merchant.get("mcc_autopay_share") or 0.0)

        w = cfg.merchant_priority_weights
        score = round(
            w["growth"] * growth_score + w["success_rate"] * success_score
            + w["scale"] * scale_score + w["category"] * category_score, 2
        )
        if score >= cfg.merchant_high_priority_score:
            tier = "HIGH"
        elif score >= cfg.merchant_medium_priority_score:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return self.info(
            f"Merchant priority score {score:.1f}/100 — {tier} priority tier.",
            evidence={
                "priority_score": score, "priority_tier": tier,
                "components": {
                    "growth": round(growth_score, 1),
                    "success_rate": round(success_score, 1),
                    "scale": round(scale_score, 1),
                    "category": round(category_score, 1),
                },
                "weights": dict(w),
            },
            recommendation={
                "HIGH": "Assign to the strategic account program.",
                "MEDIUM": "Include in standard growth campaigns.",
                "LOW": "Monitor; no dedicated investment yet.",
            }[tier],
        )
