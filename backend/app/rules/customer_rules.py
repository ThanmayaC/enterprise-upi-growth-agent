"""Customer rules (priority 50–59) — behaviour, value, and engagement.

Consume the customer-behaviour prediction bundle (expected usage, activity
level, retention probability) plus the customer's activity analytics.
"""

from __future__ import annotations

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity


class CustomerRetentionRule(BaseRule):
    """Predicted retention must clear the configured churn threshold."""

    name = "customer_retention"
    category = "customer"
    priority = 50
    description = "Predicted retention probability clears the churn bar."

    def evaluate(self, context: RuleContext) -> RuleResult:
        record = context.prediction("customer_behaviour")
        retention = record.get("retention_probability")
        if retention is None:
            return self.warning("No retention prediction in context.")
        threshold = context.config.customer_retention_risk_threshold
        retention = float(retention)
        evidence = {"retention_probability": round(retention, 4),
                    "threshold": threshold,
                    "model": record.get("model"),
                    "version": record.get("version")}
        if retention < threshold:
            return self.failed(
                f"Retention probability {retention:.2f} is below the "
                f"{threshold:.2f} threshold — churn risk.",
                severity=RuleSeverity.MEDIUM, evidence=evidence,
                recommendation="Prioritize retention outreach for this customer.",
            )
        return self.passed(
            f"Retention probability {retention:.2f} clears the threshold.",
            evidence=evidence,
        )


class CustomerActivityLevelRule(BaseRule):
    """Predicted next-period activity level informs engagement strategy."""

    name = "customer_activity_level"
    category = "customer"
    priority = 52
    description = "Predicted activity level is Occasional or better."

    def evaluate(self, context: RuleContext) -> RuleResult:
        record = context.prediction("customer_behaviour")
        level = record.get("activity_level")
        usage = record.get("expected_usage")
        if level is None:
            return self.warning("No activity-level prediction in context.")
        evidence = {"activity_level": level,
                    "expected_usage": usage,
                    "model": record.get("model"),
                    "version": record.get("version")}
        if level == "Dormant":
            return self.warning(
                "Predicted activity level is Dormant.",
                evidence=evidence,
                recommendation="Route to the reactivation campaign.",
            )
        return self.passed(
            f"Predicted activity level is {level} "
            f"(≈{float(usage or 0):.0f} transactions next period).",
            evidence=evidence,
        )


class CustomerValueTierRule(BaseRule):
    """Classify the customer's value tier from predicted usage."""

    name = "customer_value_tier"
    category = "customer"
    priority = 54
    description = "Value tier from predicted usage vs. the power-user bar."

    def evaluate(self, context: RuleContext) -> RuleResult:
        record = context.prediction("customer_behaviour")
        usage = record.get("expected_usage")
        if usage is None:
            return self.info("No usage prediction — value tier not assigned.")
        power_bar = context.config.customer_power_usage_threshold
        usage = float(usage)
        tier = "POWER" if usage >= power_bar else (
            "REGULAR" if usage >= power_bar / 3 else "LIGHT")
        return self.info(
            f"Customer value tier {tier} "
            f"(expected usage ≈{usage:.0f}, power bar {power_bar:.0f}).",
            evidence={"value_tier": tier, "expected_usage": round(usage, 2),
                      "power_bar": power_bar},
            recommendation={
                "POWER": "Offer premium journeys and Autopay bundles.",
                "REGULAR": "Include in standard engagement campaigns.",
                "LIGHT": "Nurture with low-touch education nudges.",
            }[tier],
        )
