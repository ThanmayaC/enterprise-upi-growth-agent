"""Retry rules (priority 40–49, category ``retry``) — failed-transaction
retry governance.

Combine hard product limits (attempt caps), error semantics (retryable
error classes from the error master, supplied via context), and the ML
success prediction to decide whether an automatic retry is justified.
"""

from __future__ import annotations

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity


class RetryAttemptLimitRule(BaseRule):
    """Never exceed the configured maximum automatic retries."""

    name = "retry_attempt_limit"
    category = "retry"
    priority = 40
    description = "Attempt count is below the configured retry maximum."

    def evaluate(self, context: RuleContext) -> RuleResult:
        attempts = int(context.extras.get("attempts", 0))
        limit = context.config.retry_max_attempts
        if attempts >= limit:
            return self.failed(
                f"{attempts} attempts already made — the retry limit "
                f"({limit}) is exhausted.",
                severity=RuleSeverity.CRITICAL,
                evidence={"attempts": attempts, "retry_limit": limit},
                recommendation="Stop automatic retries; move to manual follow-up.",
            )
        return self.passed(
            f"{attempts} of {limit} allowed attempts used.",
            evidence={"attempts": attempts, "retry_limit": limit},
        )


class RetryableErrorRule(BaseRule):
    """Only retryable error classes qualify for automatic retry."""

    name = "retryable_error"
    category = "retry"
    priority = 42
    description = "The failure's error class is marked retryable."

    def evaluate(self, context: RuleContext) -> RuleResult:
        txn = context.transaction or {}
        error_code = txn.get("error_code")
        retryable = txn.get("error_retryable")
        if not error_code:
            return self.info("No error code — the transaction did not fail.")
        if retryable is None:
            return self.warning(
                f"Error {error_code} has no retryability metadata.",
                evidence={"error_code": error_code},
                recommendation="Enrich context from the error master.",
            )
        is_retryable = str(retryable).strip().lower() in ("true", "y", "yes", "1")
        if not is_retryable:
            return self.failed(
                f"Error {error_code} is a non-retryable class.",
                severity=RuleSeverity.HIGH,
                evidence={"error_code": error_code, "retryable": str(retryable)},
                recommendation="Do not retry; resolve the underlying decline.",
            )
        return self.passed(
            f"Error {error_code} is retryable.",
            evidence={"error_code": error_code, "retryable": str(retryable)},
        )


class RetrySuccessProbabilityRule(BaseRule):
    """A retry must have a fighting chance per the ML success model."""

    name = "retry_success_probability"
    category = "retry"
    priority = 44
    description = "Predicted success probability justifies a retry."

    def evaluate(self, context: RuleContext) -> RuleResult:
        record = context.prediction("transaction_success")
        probability = record.get("probability_success")
        if probability is None:
            return self.warning(
                "No success prediction in context — retry value unknown.",
                recommendation="Attach the transaction-success prediction.",
            )
        floor = context.config.retry_min_success_probability
        probability = float(probability)
        evidence = {"probability_success": round(probability, 4),
                    "floor": floor,
                    "model": record.get("model"),
                    "version": record.get("version")}
        if probability < floor:
            return self.failed(
                f"Predicted success probability {probability:.2f} is below "
                f"the retry floor {floor:.2f}.",
                severity=RuleSeverity.MEDIUM, evidence=evidence,
                recommendation="Skip the retry; queue for alternate handling.",
            )
        return self.passed(
            f"Predicted success probability {probability:.2f} clears the "
            f"retry floor {floor:.2f}.",
            evidence=evidence,
        )
