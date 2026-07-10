"""Enterprise Rule Engine — configurable business rules over Analytics + ML.

Layering (dependency direction, inward only):

    Decision Intelligence → [Rules] → (reads a prepared RuleContext only)

Rules never touch the database, services, or ML code: the Decision layer
assembles a :class:`RuleContext` (analytics facts, ML predictions, NPCI
configuration, entity data) and the engine evaluates registered rules in
priority order with full decision tracing and chaining.

``build_default_engine()`` returns an engine loaded with the complete
platform rule catalog (22 rules across 9 modules).
"""

from app.rules.autopay_rules import (
    AutopayAdoptionPredictionRule,
    AutopayAmountLimitRule,
    AutopayRecurringUsageRule,
)
from app.rules.base_rule import BaseRule
from app.rules.compliance_rules import (
    AmountCapComplianceRule,
    MandateValidityRule,
    MccComplianceRule,
)
from app.rules.customer_rules import (
    CustomerActivityLevelRule,
    CustomerRetentionRule,
    CustomerValueTierRule,
)
from app.rules.eligibility_rules import (
    AutopayEligibilityRule,
    CustomerProgramEligibilityRule,
    MerchantProgramEligibilityRule,
)
from app.rules.merchant_rules import (
    MerchantGrowthOutlookRule,
    MerchantPriorityScoreRule,
    MerchantScaleRule,
    MerchantSuccessRateRule,
)
from app.rules.npci_config import NpciRuleConfig
from app.rules.recommendation_rules import (
    CustomerActionRecommendationRule,
    MerchantActionRecommendationRule,
    RetryActionRecommendationRule,
)
from app.rules.retry_rules import (
    RetryableErrorRule,
    RetryAttemptLimitRule,
    RetrySuccessProbabilityRule,
)
from app.rules.risk_rules import (
    CustomerChurnRiskRule,
    FailureRateRiskRule,
    HighAmountRiskRule,
)
from app.rules.rule_context import RuleContext
from app.rules.rule_engine import RuleEngine, RuleReport
from app.rules.rule_result import RuleResult, RuleSeverity, RuleStatus
from app.rules.validation_rules import (
    AmountValidationRule,
    ContextCompletenessRule,
    PredictionConfidenceRule,
)

#: The complete platform rule catalog, grouped by module.
ALL_RULES: list[type[BaseRule]] = [
    # validation (10–19)
    ContextCompletenessRule, AmountValidationRule, PredictionConfidenceRule,
    # compliance (20–29)
    AmountCapComplianceRule, MccComplianceRule, MandateValidityRule,
    # risk (30–39)
    HighAmountRiskRule, FailureRateRiskRule, CustomerChurnRiskRule,
    # domain (40–69)
    AutopayAdoptionPredictionRule, AutopayRecurringUsageRule,
    AutopayAmountLimitRule,
    MerchantGrowthOutlookRule, MerchantSuccessRateRule, MerchantScaleRule,
    MerchantPriorityScoreRule,
    CustomerRetentionRule, CustomerActivityLevelRule, CustomerValueTierRule,
    RetryAttemptLimitRule, RetryableErrorRule, RetrySuccessProbabilityRule,
    # eligibility (70–79, chained)
    AutopayEligibilityRule, MerchantProgramEligibilityRule,
    CustomerProgramEligibilityRule,
    # recommendation (90–99, chained)
    MerchantActionRecommendationRule, CustomerActionRecommendationRule,
    RetryActionRecommendationRule,
]


def build_default_engine() -> RuleEngine:
    """A rule engine loaded with the full platform catalog."""

    return RuleEngine().register_all(rule_cls() for rule_cls in ALL_RULES)


__all__ = [
    "ALL_RULES",
    "BaseRule",
    "NpciRuleConfig",
    "RuleContext",
    "RuleEngine",
    "RuleReport",
    "RuleResult",
    "RuleSeverity",
    "RuleStatus",
    "build_default_engine",
]
