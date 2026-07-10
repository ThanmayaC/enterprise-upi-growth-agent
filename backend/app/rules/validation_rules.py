"""Validation rules (priority 10–19) — is the context fit to decide on?

These run first: they guard every downstream rule against missing or
malformed inputs, so domain rules can assume a sane context.
"""

from __future__ import annotations

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity


class ContextCompletenessRule(BaseRule):
    """The evaluation must concern at least one subject entity."""

    name = "context_completeness"
    category = "validation"
    priority = 10
    description = "A merchant, customer, or transaction subject is present."

    def evaluate(self, context: RuleContext) -> RuleResult:
        present = [k for k, v in (
            ("merchant", context.merchant),
            ("customer", context.customer),
            ("transaction", context.transaction),
        ) if v]
        if not present:
            return self.failed(
                "No subject entity (merchant/customer/transaction) in context.",
                severity=RuleSeverity.CRITICAL,
                recommendation="Supply the subject before requesting a decision.",
            )
        return self.passed(
            f"Context contains subject data for: {', '.join(present)}.",
            evidence={"subjects": present,
                      "predictions": sorted(context.predictions)},
        )


class AmountValidationRule(BaseRule):
    """A transaction amount, when present, must be a positive number."""

    name = "amount_validation"
    category = "validation"
    priority = 12
    description = "Transaction amount is positive and numeric."

    def evaluate(self, context: RuleContext) -> RuleResult:
        txn = context.transaction
        if not txn or "amount" not in txn:
            return self.info("No transaction amount to validate.")
        try:
            amount = float(txn["amount"])
        except (TypeError, ValueError):
            return self.failed(
                f"Transaction amount {txn['amount']!r} is not numeric.",
                severity=RuleSeverity.CRITICAL,
                evidence={"amount": str(txn["amount"])},
                recommendation="Correct the amount before processing.",
            )
        if amount <= 0:
            return self.failed(
                f"Transaction amount {amount} must be positive.",
                severity=RuleSeverity.CRITICAL,
                evidence={"amount": amount},
                recommendation="Correct the amount before processing.",
            )
        return self.passed(f"Amount {amount:,.2f} is valid.",
                           evidence={"amount": amount})


class PredictionConfidenceRule(BaseRule):
    """Low-confidence ML predictions are advisory, not decisive."""

    name = "prediction_confidence"
    category = "validation"
    priority = 15
    description = "Every ML prediction meets the minimum confidence bar."

    def evaluate(self, context: RuleContext) -> RuleResult:
        floor = context.config.risk_min_confidence
        weak = {
            key: rec.get("confidence")
            for key, rec in context.predictions.items()
            if rec.get("confidence") is not None
            and float(rec["confidence"]) < floor
        }
        if weak:
            return self.warning(
                f"{len(weak)} prediction(s) below confidence floor {floor}: "
                f"{sorted(weak)} — treated as advisory.",
                evidence={"weak_predictions": weak, "confidence_floor": floor},
                recommendation="Weight these predictions lower in the decision.",
            )
        return self.passed(
            "All supplied predictions meet the confidence floor.",
            evidence={"confidence_floor": floor,
                      "predictions": sorted(context.predictions)},
        )
