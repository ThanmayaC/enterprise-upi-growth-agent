"""Recommendation rules (priority 90–99) — the last word in every run.

These INFO-status rules chain over everything before them and translate
outcomes into one concrete, business-ready next action. They never block;
they direct.
"""

from __future__ import annotations

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleStatus


class MerchantActionRecommendationRule(BaseRule):
    """Recommend the next merchant action from the chained outcomes."""

    name = "merchant_action_recommendation"
    category = "recommendation"
    priority = 90
    description = "Concrete next action for the merchant, from all outcomes."

    def evaluate(self, context: RuleContext) -> RuleResult:
        if context.merchant is None:
            return self.info("No merchant subject — no merchant action.")
        priority_rows = context.prior(rule_name="merchant_priority_score")
        tier = (priority_rows[0].evidence.get("priority_tier")
                if priority_rows else None)
        autopay_rows = context.prior(rule_name="autopay_eligibility")
        autopay_ok = bool(autopay_rows and autopay_rows[0].passed)
        growth_rows = context.prior(rule_name="merchant_growth_outlook")
        declining = bool(growth_rows
                         and growth_rows[0].status is RuleStatus.WARNING)

        if declining:
            action = "ENROLL_IN_RETENTION_PROGRAM"
            reason = "Growth outlook is declining — retention comes first."
        elif autopay_ok and tier == "HIGH":
            action = "PRIORITIZE_AUTOPAY_ONBOARDING"
            reason = "High-priority merchant, eligible for Autopay."
        elif autopay_ok:
            action = "OFFER_AUTOPAY_MANDATES"
            reason = "Autopay-eligible; standard mandate outreach."
        elif tier == "HIGH":
            action = "ASSIGN_STRATEGIC_ACCOUNT_MANAGER"
            reason = "High-priority merchant outside the Autopay track."
        else:
            action = "INCLUDE_IN_STANDARD_GROWTH_CAMPAIGN"
            reason = "No special track indicated by the evaluated rules."
        return self.info(
            f"Recommended merchant action: {action}. {reason}",
            evidence={"action": action, "priority_tier": tier,
                      "autopay_eligible": autopay_ok,
                      "growth_declining": declining},
            recommendation=action,
        )


class CustomerActionRecommendationRule(BaseRule):
    """Recommend the next customer action from the chained outcomes."""

    name = "customer_action_recommendation"
    category = "recommendation"
    priority = 92
    description = "Concrete next action for the customer, from all outcomes."

    def evaluate(self, context: RuleContext) -> RuleResult:
        if context.customer is None:
            return self.info("No customer subject — no customer action.")
        churn_rows = context.prior(rule_name="customer_churn_risk")
        churn_risk = bool(churn_rows
                          and churn_rows[0].status is RuleStatus.WARNING)
        retention_rows = context.prior(rule_name="customer_retention")
        retention_fail = bool(retention_rows and retention_rows[0].failed)
        tier_rows = context.prior(rule_name="customer_value_tier")
        tier = (tier_rows[0].evidence.get("value_tier")
                if tier_rows else None)
        level_rows = context.prior(rule_name="customer_activity_level")
        dormant = bool(level_rows
                       and level_rows[0].status is RuleStatus.WARNING)

        if retention_fail or churn_risk:
            action = "LAUNCH_RETENTION_CAMPAIGN"
            reason = "Churn indicators dominate — retain before growing."
        elif dormant:
            action = "TRIGGER_REACTIVATION_JOURNEY"
            reason = "Predicted dormancy calls for reactivation."
        elif tier == "POWER":
            action = "OFFER_AUTOPAY_AND_PREMIUM_JOURNEYS"
            reason = "Power user — deepen engagement with mandates."
        else:
            action = "INCLUDE_IN_STANDARD_ENGAGEMENT"
            reason = "Healthy profile; standard engagement suffices."
        return self.info(
            f"Recommended customer action: {action}. {reason}",
            evidence={"action": action, "value_tier": tier,
                      "churn_risk": churn_risk, "dormant": dormant},
            recommendation=action,
        )


class RetryActionRecommendationRule(BaseRule):
    """Recommend the retry handling from the chained retry outcomes."""

    name = "retry_action_recommendation"
    category = "recommendation"
    priority = 94
    description = "Concrete retry handling for the failed transaction."

    def evaluate(self, context: RuleContext) -> RuleResult:
        retry_results = context.prior(category="retry")
        if not retry_results:
            return self.info("No retry evaluation — no retry action.")
        failures = [r for r in retry_results if r.failed]
        if failures:
            action = "DO_NOT_RETRY"
            reason = ("Blocked by: "
                      + ", ".join(r.rule_name for r in failures) + ".")
        else:
            action = "SCHEDULE_AUTOMATIC_RETRY"
            reason = "All retry gates passed."
        return self.info(
            f"Recommended retry action: {action}. {reason}",
            evidence={"action": action,
                      "blocking_rules": [r.rule_name for r in failures]},
            recommendation=action,
        )
