"""Compliance rules (priority 20–29) — hard NPCI product-rule boundaries.

Violations here are blocking by design: they encode published product
limits (amount caps, MCC whitelists, mandate validity), all sourced from
:class:`NpciRuleConfig` — never hardcoded.
"""

from __future__ import annotations

from datetime import date, datetime

from app.rules.base_rule import BaseRule
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult, RuleSeverity


class AmountCapComplianceRule(BaseRule):
    """No transaction may exceed the configured UPI amount ceiling."""

    name = "amount_cap_compliance"
    category = "compliance"
    priority = 20
    description = "Transaction amount is within the UPI ceiling."

    def evaluate(self, context: RuleContext) -> RuleResult:
        txn = context.transaction
        cap = context.config.high_amount_threshold
        if not txn or "amount" not in txn:
            return self.info("No transaction amount — amount cap not applicable.")
        amount = float(txn["amount"])
        if amount > cap:
            return self.failed(
                f"Amount {amount:,.0f} exceeds the ceiling {cap:,.0f}.",
                severity=RuleSeverity.CRITICAL,
                evidence={"amount": amount, "ceiling": cap},
                recommendation="Reject or route through an approved high-value flow.",
            )
        return self.passed(
            f"Amount {amount:,.0f} is within the ceiling {cap:,.0f}.",
            evidence={"amount": amount, "ceiling": cap},
        )


class MccComplianceRule(BaseRule):
    """Autopay may only be offered in whitelisted merchant categories."""

    name = "mcc_compliance"
    category = "compliance"
    priority = 22
    description = "Merchant MCC is on the configured Autopay whitelist."

    def evaluate(self, context: RuleContext) -> RuleResult:
        allowed = context.config.autopay_allowed_mcc
        merchant = context.merchant or {}
        mcc = str(merchant.get("mcc_code") or "").strip()
        if not allowed:
            return self.info("MCC whitelist empty — no category restriction.")
        if not mcc:
            return self.info("No merchant MCC in context — check skipped.")
        if mcc not in allowed:
            return self.failed(
                f"MCC {mcc} is not on the Autopay whitelist "
                f"({len(allowed)} categories).",
                severity=RuleSeverity.HIGH,
                evidence={"mcc_code": mcc, "whitelist_size": len(allowed)},
                recommendation="Exclude from mandate programs or seek approval.",
            )
        return self.passed(f"MCC {mcc} is whitelisted for Autopay.",
                           evidence={"mcc_code": mcc})


class MandateValidityRule(BaseRule):
    """Mandate validity windows must be ordered and within the maximum."""

    name = "mandate_validity"
    category = "compliance"
    priority = 24
    description = "Mandate validity window is well-formed and within limits."

    @staticmethod
    def _to_date(value) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()

    def evaluate(self, context: RuleContext) -> RuleResult:
        txn = context.transaction or {}
        start = self._to_date(txn.get("mandate_validity_start"))
        end = self._to_date(txn.get("mandate_validity_end"))
        if start is None or end is None:
            return self.info("No mandate validity window — check not applicable.")
        max_days = context.config.mandate_max_validity_days
        days = (end - start).days
        if days < 0:
            return self.failed(
                f"Validity end {end} precedes start {start}.",
                severity=RuleSeverity.CRITICAL,
                evidence={"start": str(start), "end": str(end)},
                recommendation="Correct the mandate window.",
            )
        if days > max_days:
            return self.failed(
                f"Validity window {days} days exceeds the {max_days}-day limit.",
                severity=RuleSeverity.HIGH,
                evidence={"days": days, "max_days": max_days},
                recommendation="Shorten the mandate validity window.",
            )
        return self.passed(
            f"Mandate window of {days} days is within the {max_days}-day limit.",
            evidence={"days": days, "max_days": max_days},
        )
