"""NPCI product rule configuration — no product rule is hardcoded.

Every configurable business threshold used by the rule modules lives here
as a typed, documented field with an enterprise default. Deployments (or
tests) override values via :meth:`NpciRuleConfig.with_overrides` — rules
only ever read ``context.config``, never module constants.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from typing import Any

#: Default MCC whitelist for Autopay mandates (empty set ⇒ all MCCs allowed).
_DEFAULT_AUTOPAY_MCC: frozenset[str] = frozenset({
    "4111", "4121", "4131", "4511",          # transit & travel
    "4814", "4899", "4900",                  # telecom, cable/OTT, utilities
    "5411", "5912", "5968",                  # groceries, pharmacy, subscriptions
    "6211", "6300",                          # securities, insurance
    "8011", "8211", "8220", "8299", "8398",  # health, education, NGOs
})


@dataclass(frozen=True)
class NpciRuleConfig:
    """All configurable product rules (defaults reflect NPCI-style limits)."""

    # --- Autopay / mandate product rules ----------------------------------
    autopay_max_amount: float = 15_000.0
    """Maximum per-execution mandate amount without additional factor."""

    autopay_min_adoption_probability: float = 0.60
    """ML adoption probability at/above which a subject counts as 'High'."""

    autopay_min_recurring_share: float = 0.15
    """Minimum recurring/autopay share of category traffic to qualify."""

    autopay_allowed_mcc: frozenset[str] = _DEFAULT_AUTOPAY_MCC
    """MCCs where mandates may be offered (empty ⇒ no MCC restriction)."""

    mandate_max_validity_days: int = 3_650
    """Longest permissible mandate validity window."""

    # --- Retry product rules ----------------------------------------------
    retry_max_attempts: int = 3
    """Maximum automatic retries for a failed transaction."""

    retry_min_success_probability: float = 0.30
    """ML success probability below which a retry is not worth attempting."""

    # --- Frequency rules -----------------------------------------------------
    daily_transaction_frequency_limit: int = 20
    """Per-customer daily transaction count treated as normal ceiling."""

    # --- Merchant eligibility / priority -------------------------------------
    merchant_min_success_rate: float = 85.0
    """Minimum success rate (%) for program eligibility."""

    merchant_min_period_transactions: int = 100
    """Minimum transactions in the observation window for eligibility."""

    merchant_priority_weights: dict[str, float] = field(default_factory=lambda: {
        "growth": 0.40, "success_rate": 0.25, "scale": 0.25, "category": 0.10,
    })
    """Weights of the merchant priority score components (sum to 1)."""

    merchant_high_priority_score: float = 70.0
    merchant_medium_priority_score: float = 45.0
    """Priority-tier cutoffs on the 0–100 priority score."""

    # --- Customer rules ----------------------------------------------------
    customer_retention_risk_threshold: float = 0.50
    """Retention probability below this ⇒ churn risk."""

    customer_power_usage_threshold: float = 10.0
    """Predicted next-period usage at/above this ⇒ power user."""

    # --- Risk thresholds ------------------------------------------------------
    high_amount_threshold: float = 100_000.0
    """Single-transaction amount treated as high value (UPI ceiling)."""

    risk_failure_rate_threshold: float = 20.0
    """Entity failure rate (%) above which reliability risk is flagged."""

    risk_min_confidence: float = 0.35
    """ML confidence below which predictions are advisory only."""

    # ------------------------------------------------------------------
    def with_overrides(self, overrides: dict[str, Any] | None) -> "NpciRuleConfig":
        """Return a copy with ``overrides`` applied (unknown keys rejected)."""

        if not overrides:
            return self
        valid = {f.name for f in fields(self)}
        unknown = set(overrides) - valid
        if unknown:
            raise KeyError(f"unknown NPCI config keys: {sorted(unknown)}")
        return replace(self, **overrides)

    def to_dict(self) -> dict[str, Any]:
        return {
            f.name: (sorted(v) if isinstance(v := getattr(self, f.name), frozenset) else v)
            for f in fields(self)
        }
