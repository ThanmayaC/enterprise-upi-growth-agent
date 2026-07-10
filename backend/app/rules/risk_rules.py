"""Risk rules (priority 30–39) — surface risk, usually as warnings.

Risk findings rarely block on their own; they condition the decision
(APPROVED → APPROVED_WITH_CONDITIONS) and feed the evidence trail.
"""

from __future__ import annotations

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult


class HighAmountRiskRule(BaseRule):
    """Amounts near the ceiling warrant closer scrutiny."""

    name = "high_amount_risk"
    category = "risk"
    priority = 30
    description = "Transaction amount is not unusually large."

    def evaluate(self, context: RuleContext) -> RuleResult:
        txn = context.transaction
        if not txn or "amount" not in txn:
            return self.info("No transaction amount — risk check skipped.")
        amount = float(txn["amount"])
        watch_level = 0.5 * context.config.high_amount_threshold
        if amount > watch_level:
            return self.warning(
                f"Amount {amount:,.0f} exceeds the high-value watch level "
                f"{watch_level:,.0f}.",
                evidence={"amount": amount, "watch_level": watch_level},
                recommendation="Apply enhanced verification for this amount band.",
            )
        return self.passed(f"Amount {amount:,.0f} is in the normal band.",
                           evidence={"amount": amount, "watch_level": watch_level})


class FailureRateRiskRule(BaseRule):
    """Entities with elevated failure rates carry reliability risk."""

    name = "failure_rate_risk"
    category = "risk"
    priority = 32
    description = "Subject's observed failure rate is under the risk threshold."

    def evaluate(self, context: RuleContext) -> RuleResult:
        merchant = context.merchant or {}
        success_rate = merchant.get("success_rate")
        if success_rate is None:
            return self.info("No success-rate analytics — risk check skipped.")
        failure_rate = round(100.0 - float(success_rate), 2)
        threshold = context.config.risk_failure_rate_threshold
        if failure_rate > threshold:
            return self.warning(
                f"Failure rate {failure_rate:.1f}% exceeds the "
                f"{threshold:.0f}% risk threshold.",
                evidence={"failure_rate_pct": failure_rate,
                          "threshold_pct": threshold},
                recommendation="Trigger a reliability remediation review.",
            )
        return self.passed(
            f"Failure rate {failure_rate:.1f}% is within tolerance.",
            evidence={"failure_rate_pct": failure_rate,
                      "threshold_pct": threshold},
        )


class CustomerChurnRiskRule(BaseRule):
    """Low predicted retention flags churn risk on customer decisions."""

    name = "customer_churn_risk"
    category = "risk"
    priority = 34
    description = "Predicted retention probability is above the churn threshold."

    def evaluate(self, context: RuleContext) -> RuleResult:
        record = context.prediction("customer_behaviour")
        retention = record.get("retention_probability")
        if retention is None:
            return self.info("No retention prediction — churn check skipped.")
        threshold = context.config.customer_retention_risk_threshold
        retention = float(retention)
        if retention < threshold:
            return self.warning(
                f"Retention probability {retention:.2f} is below the churn "
                f"threshold {threshold:.2f}.",
                evidence={"retention_probability": retention,
                          "threshold": threshold,
                          "model": record.get("model"),
                          "version": record.get("version")},
                recommendation="Enroll the customer in a retention program.",
            )
        return self.passed(
            f"Retention probability {retention:.2f} indicates low churn risk.",
            evidence={"retention_probability": retention, "threshold": threshold},
        )
