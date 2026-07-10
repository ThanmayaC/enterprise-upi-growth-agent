"""Tool registry — the Copilot's catalogue of backend capabilities.

Each tool is a thin, declarative wrapper that **calls an existing service
facade** and returns its output unchanged. No tool touches the database, a
repository, or an ORM model: they reach only into the frozen Analytics, ML
Intelligence, and Decision Intelligence facades. This is what keeps the
Copilot an orchestration layer rather than a second implementation of the
platform's logic.

The :class:`CopilotServices` container builds those facades from one request
session, reusing the exact constructor wiring of ``app.api.core.dependencies``
(Repositories → Services → Analytics) so there is a single source of truth for
how the stack is assembled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.analytics import (
    BankAnalytics,
    CustomerAnalytics,
    MerchantAnalytics,
    PortfolioAnalytics,
    PspAnalytics,
    TimeAnalytics,
)
from app.copilot.copilot_models import Intent, ReferencedEntities
from app.decision import DecisionIntelligenceService
from app.ml.prediction import MLIntelligenceService
from app.repositories import (
    BankRepository,
    CustomerRepository,
    MerchantRepository,
    PspRepository,
    TransactionRepository,
)
from app.services import (
    BankService,
    CustomerService,
    KpiService,
    MerchantService,
    PortfolioService,
    PspService,
    TransactionService,
)


class CopilotServices:
    """Lazily-built container of every facade the tools may call.

    The wiring mirrors ``app.api.core.dependencies`` exactly; facades are
    created on first access so a portfolio question never instantiates the
    ML engine, and vice-versa.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- repositories (internal, never exposed to tools) ------------------
    @cached_property
    def _tx_repo(self) -> TransactionRepository:
        return TransactionRepository(self._session)

    @cached_property
    def _merchant_repo(self) -> MerchantRepository:
        return MerchantRepository(self._session)

    @cached_property
    def _customer_repo(self) -> CustomerRepository:
        return CustomerRepository(self._session)

    @cached_property
    def _bank_repo(self) -> BankRepository:
        return BankRepository(self._session)

    @cached_property
    def _psp_repo(self) -> PspRepository:
        return PspRepository(self._session)

    # --- services ---------------------------------------------------------
    @cached_property
    def _kpi(self) -> KpiService:
        return KpiService(self._tx_repo, self._merchant_repo)

    @cached_property
    def _transactions(self) -> TransactionService:
        return TransactionService(self._tx_repo, self._kpi)

    @cached_property
    def merchants(self) -> MerchantService:
        return MerchantService(self._merchant_repo, self._tx_repo)

    @cached_property
    def customers(self) -> CustomerService:
        return CustomerService(self._customer_repo, self._tx_repo)

    @cached_property
    def banks(self) -> BankService:
        return BankService(self._bank_repo, self._tx_repo)

    @cached_property
    def psps(self) -> PspService:
        return PspService(self._psp_repo, self._tx_repo)

    @cached_property
    def portfolio(self) -> PortfolioService:
        return PortfolioService(
            self._kpi, self._tx_repo, self._bank_repo,
            self._psp_repo, self._customer_repo, self._merchant_repo,
        )

    # --- analytics --------------------------------------------------------
    @cached_property
    def time_analytics(self) -> TimeAnalytics:
        return TimeAnalytics(self._transactions)

    @cached_property
    def portfolio_analytics(self) -> PortfolioAnalytics:
        return PortfolioAnalytics(self.portfolio, self._kpi, self.time_analytics)

    @cached_property
    def merchant_analytics(self) -> MerchantAnalytics:
        return MerchantAnalytics(self.merchants)

    @cached_property
    def customer_analytics(self) -> CustomerAnalytics:
        return CustomerAnalytics(self.customers)

    @cached_property
    def bank_analytics(self) -> BankAnalytics:
        return BankAnalytics(self.banks)

    @cached_property
    def psp_analytics(self) -> PspAnalytics:
        return PspAnalytics(self.psps)

    # --- ML + decision facades -------------------------------------------
    @cached_property
    def ml(self) -> MLIntelligenceService:
        return MLIntelligenceService(self._session)

    @cached_property
    def decision(self) -> DecisionIntelligenceService:
        return DecisionIntelligenceService(self._session)


@dataclass(frozen=True)
class Tool:
    """A registered backend capability the Copilot can orchestrate.

    Attributes:
        name: Stable identifier used in prompts and audit records.
        description: One line the LLM/planner reads to understand the tool.
        intents: Intents for which this tool is relevant.
        run: ``(services, entities) -> Any`` — invokes an existing facade.
        kind: Coarse label ("analytics" | "prediction" | "decision" | "rule")
            used by the response formatter to sort evidence into the right
            structured field.
    """

    name: str
    description: str
    intents: tuple[Intent, ...]
    run: Callable[[CopilotServices, ReferencedEntities], Any]
    kind: str = "analytics"


# ---------------------------------------------------------------------------
# Tool implementations — every body is a single call into a frozen facade.
# ---------------------------------------------------------------------------
def _portfolio_tool(s: CopilotServices, _e: ReferencedEntities) -> Any:
    return {
        "executive_snapshot": s.portfolio_analytics.get_executive_snapshot(),
        "growth_overview": s.portfolio_analytics.get_growth_overview(),
        "business_health": s.portfolio_analytics.get_business_health(),
    }


def _merchant_tool(s: CopilotServices, e: ReferencedEntities) -> Any:
    if e.merchant_id:
        return {
            "profile": s.merchants.get_merchant_profile(e.merchant_id),
            "summary": s.merchants.get_merchant_summary(e.merchant_id),
        }
    return {
        "top_merchants": s.merchant_analytics.get_top_merchants(),
        "success_rate": s.merchant_analytics.get_success_rate_analysis(),
    }


def _customer_tool(s: CopilotServices, e: ReferencedEntities) -> Any:
    if e.customer_vpa:
        return {"profile": s.customers.find_customer_by_vpa(e.customer_vpa)}
    return {
        "top_customers": s.customer_analytics.get_top_customers(),
        "activity_distribution": s.customer_analytics.get_activity_distribution(),
    }


def _bank_tool(s: CopilotServices, _e: ReferencedEntities) -> Any:
    return {
        "rankings": s.bank_analytics.get_bank_rankings(),
        "issuers": s.bank_analytics.get_issuer_analysis(),
        "acquirers": s.bank_analytics.get_acquirer_analysis(),
    }


def _psp_tool(s: CopilotServices, _e: ReferencedEntities) -> Any:
    return {
        "rankings": s.psp_analytics.get_psp_rankings(),
        "performance": s.psp_analytics.get_psp_performance(),
        "success_analysis": s.psp_analytics.get_success_analysis(),
    }


def _time_tool(s: CopilotServices, _e: ReferencedEntities) -> Any:
    return {"monthly_trend": s.time_analytics.get_monthly_trend()}


def _growth_prediction_tool(s: CopilotServices, e: ReferencedEntities) -> Any:
    return {"merchant_growth": s.ml.merchant_growth_predictions(
        top_n=10, merchant_id=e.merchant_id)}


def _autopay_prediction_tool(s: CopilotServices, _e: ReferencedEntities) -> Any:
    return {"autopay_opportunities": s.ml.autopay_opportunities(top_n=10)}


def _transaction_success_tool(s: CopilotServices, e: ReferencedEntities) -> Any:
    # A transaction-shaped payload is required; when the user has not supplied
    # one we surface the model catalogue entry rather than inventing inputs.
    return {"note": "Provide a transaction payload to score success.",
            "model_catalog": [
                m for m in s.ml.model_catalog()
                if m["name"] == "transaction_success"
            ]}


def _decision_tool(s: CopilotServices, e: ReferencedEntities) -> Any:
    if e.merchant_id:
        return {
            "autopay_eligibility": s.decision.evaluate_autopay_eligibility(
                e.merchant_id),
            "merchant_priority": s.decision.evaluate_merchant_priority(
                e.merchant_id),
        }
    if e.customer_vpa:
        return {"customer_recommendation":
                s.decision.evaluate_customer_recommendation(e.customer_vpa)}
    return {"note": "Reference a merchant (MER…) or customer VPA for a decision.",
            "active_configuration": s.decision.active_configuration()}


def _rule_catalog_tool(s: CopilotServices, _e: ReferencedEntities) -> Any:
    return {"rule_catalog": s.decision.rule_catalog(),
            "active_configuration": s.decision.active_configuration()}


def _model_catalog_tool(s: CopilotServices, _e: ReferencedEntities) -> Any:
    return {"model_catalog": s.ml.model_catalog()}


def _default_registry() -> dict[str, Tool]:
    """Build the immutable set of tools the Copilot ships with."""

    tools = [
        Tool("portfolio_tool",
             "Executive portfolio snapshot, growth overview, business health.",
             (Intent.PORTFOLIO_ANALYSIS,), _portfolio_tool, "analytics"),
        Tool("merchant_tool",
             "Merchant profile/summary, or top merchants and success rates.",
             (Intent.MERCHANT_ANALYSIS,), _merchant_tool, "analytics"),
        Tool("customer_tool",
             "Customer lifetime summary, or top customers and activity mix.",
             (Intent.CUSTOMER_ANALYSIS,), _customer_tool, "analytics"),
        Tool("bank_tool",
             "Issuer/acquirer rankings and analysis.",
             (Intent.BANK_ANALYSIS,), _bank_tool, "analytics"),
        Tool("psp_tool",
             "PSP rankings, performance, and success analysis.",
             (Intent.PSP_ANALYSIS,), _psp_tool, "analytics"),
        Tool("analytics_time_tool",
             "Monthly time-series trend across the portfolio.",
             (Intent.PORTFOLIO_ANALYSIS, Intent.GROWTH_OPPORTUNITY),
             _time_tool, "analytics"),
        Tool("ml_growth_tool",
             "ML merchant growth predictions with confidence.",
             (Intent.GROWTH_OPPORTUNITY,), _growth_prediction_tool, "prediction"),
        Tool("ml_autopay_tool",
             "ML autopay opportunity scores for merchants and customers.",
             (Intent.AUTOPAY_OPPORTUNITY,), _autopay_prediction_tool, "prediction"),
        Tool("ml_transaction_success_tool",
             "Transaction success probability model surface.",
             (Intent.TRANSACTION_SUCCESS,), _transaction_success_tool, "prediction"),
        Tool("decision_tool",
             "Decision Engine verdicts (eligibility, priority, recommendation).",
             (Intent.DECISION_EXPLANATION,), _decision_tool, "decision"),
        Tool("rule_explanation_tool",
             "Business-rule catalogue and active NPCI configuration.",
             (Intent.RULE_EXPLANATION,), _rule_catalog_tool, "rule"),
        Tool("model_catalog_tool",
             "Registered ML models with status, metrics, lineage.",
             (Intent.GENERAL_PRODUCT_QUESTION,), _model_catalog_tool, "prediction"),
    ]
    return {t.name: t for t in tools}


class ToolRegistry:
    """The immutable catalogue plus intent → tools routing."""

    def __init__(self, tools: dict[str, Tool] | None = None) -> None:
        self._tools = tools or _default_registry()

    def all(self) -> list[Tool]:
        """Every registered tool."""

        return list(self._tools.values())

    def get(self, name: str) -> Tool | None:
        """Look up a tool by name."""

        return self._tools.get(name)

    def for_intent(self, intent: Intent) -> list[Tool]:
        """Tools relevant to an intent, in registration order.

        ``GENERAL_PRODUCT_QUESTION`` maps to the model-catalogue tool so even
        open-ended questions return grounded platform facts rather than free
        LLM speculation.
        """

        return [t for t in self._tools.values() if intent in t.intents]
