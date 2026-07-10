"""Autopay rules (priority 40–49) — mandate-product domain checks.

Implements the specified eligibility pattern:
    IF adoption prediction is High AND recurring share is High
    AND amount is within the configured limit THEN eligible.
The final verdict is assembled by ``AutopayEligibilityRule`` in
:mod:`eligibility_rules`, which chains over these results plus compliance.
"""

from __future__ import annotations

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity


class AutopayAdoptionPredictionRule(BaseRule):
    """The ML adoption probability must clear the configured 'High' bar."""

    name = "autopay_adoption_prediction"
    category = "autopay"
    priority = 41
    description = "ML Autopay adoption probability is high enough."

    def evaluate(self, context: RuleContext) -> RuleResult:
        record = (context.prediction("merchant_autopay")
                  or context.prediction("customer_autopay"))
        probability = record.get("adoption_probability")
        if probability is None:
            return self.warning(
                "No Autopay adoption prediction in context.",
                recommendation="Provide the autopay model output for a "
                               "prediction-backed decision.",
            )
        threshold = context.config.autopay_min_adoption_probability
        probability = float(probability)
        if probability < threshold:
            return self.failed(
                f"Adoption probability {probability:.2f} is below the "
                f"'High' threshold {threshold:.2f}.",
                severity=RuleSeverity.MEDIUM,
                evidence={"adoption_probability": probability,
                          "threshold": threshold,
                          "model": record.get("model"),
                          "version": record.get("version")},
                recommendation="Defer mandate outreach; nurture the subject first.",
            )
        return self.passed(
            f"Adoption probability {probability:.2f} clears the "
            f"'High' threshold {threshold:.2f}.",
            evidence={"adoption_probability": probability,
                      "threshold": threshold,
                      "model": record.get("model"),
                      "version": record.get("version")},
        )


class AutopayRecurringUsageRule(BaseRule):
    """The subject's category must show meaningful recurring usage."""

    name = "autopay_recurring_usage"
    category = "autopay"
    priority = 43
    description = "Observed recurring/mandate share of traffic is high enough."

    def evaluate(self, context: RuleContext) -> RuleResult:
        merchant = context.merchant or {}
        customer = context.customer or {}
        share = merchant.get("mcc_autopay_share",
                             customer.get("autopay_share"))
        if share is None:
            return self.warning(
                "No recurring-usage analytics available for the subject.",
                recommendation="Attach category autopay share to the context.",
            )
        threshold = context.config.autopay_min_recurring_share
        share = float(share)
        if share < threshold:
            return self.warning(
                f"Recurring share {share:.2%} is below the "
                f"{threshold:.0%} qualification bar.",
                evidence={"recurring_share": round(share, 4),
                          "threshold": threshold},
                recommendation="Target category-level mandate education first.",
            )
        return self.passed(
            f"Recurring share {share:.2%} meets the {threshold:.0%} bar.",
            evidence={"recurring_share": round(share, 4),
                      "threshold": threshold},
        )


class AutopayAmountLimitRule(BaseRule):
    """The mandate ticket must fit the configured Autopay amount limit."""

    name = "autopay_amount_limit"
    category = "autopay"
    priority = 45
    description = "Representative mandate amount is within the Autopay cap."

    def evaluate(self, context: RuleContext) -> RuleResult:
        limit = context.config.autopay_max_amount
        txn = context.transaction or {}
        merchant = context.merchant or {}
        amount = txn.get("amount")
        source = "transaction amount"
        if amount is None:
            amount = merchant.get("avg_ticket")
            source = "merchant average ticket"
        if amount is None:
            return self.info("No representative amount — limit check skipped.")
        amount = float(amount)
        if amount > limit:
            return self.failed(
                f"{source.capitalize()} {amount:,.0f} exceeds the Autopay "
                f"limit {limit:,.0f}.",
                severity=RuleSeverity.HIGH,
                evidence={"amount": round(amount, 2), "limit": limit,
                          "amount_source": source},
                recommendation="Restrict mandates to executions within the cap.",
            )
        return self.passed(
            f"{source.capitalize()} {amount:,.0f} fits the Autopay limit "
            f"{limit:,.0f}.",
            evidence={"amount": round(amount, 2), "limit": limit,
                      "amount_source": source},
        )
