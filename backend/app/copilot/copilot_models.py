"""Typed contracts for the Enterprise AI Product Copilot (Phase 12).

Every request and response that crosses the Copilot boundary is described
here as a Pydantic model or an enum. Keeping the vocabulary in one module
guarantees the router, the service, and the React workspace share a single,
stable schema.

The Copilot is an *orchestration* layer: these models deliberately separate
the deterministic evidence produced by the backend (analytics, predictions,
decisions, rules) from the natural-language wording produced by the LLM, so
a reviewer can always see which parts are grounded and which are prose.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Intent(str, Enum):
    """The catalogue of product questions the Copilot understands.

    Intent drives tool selection: each value maps to a deterministic set of
    backend tools in the :mod:`tool_registry`. ``GENERAL_PRODUCT_QUESTION``
    is the safe fallback for anything not backed by a specific data tool.
    """

    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    MERCHANT_ANALYSIS = "merchant_analysis"
    CUSTOMER_ANALYSIS = "customer_analysis"
    BANK_ANALYSIS = "bank_analysis"
    PSP_ANALYSIS = "psp_analysis"
    GROWTH_OPPORTUNITY = "growth_opportunity"
    AUTOPAY_OPPORTUNITY = "autopay_opportunity"
    TRANSACTION_SUCCESS = "transaction_success"
    DECISION_EXPLANATION = "decision_explanation"
    RULE_EXPLANATION = "rule_explanation"
    GENERAL_PRODUCT_QUESTION = "general_product_question"


class ReferencedEntities(BaseModel):
    """Entities the conversation is currently anchored to.

    Populated by the intent classifier from the user's message and carried
    forward by the conversation so follow-up questions ("and its success
    rate?") resolve against the last-referenced subject.
    """

    merchant_id: str | None = None
    customer_vpa: str | None = None
    bank_name: str | None = None
    psp_name: str | None = None


class ChatMessage(BaseModel):
    """One turn in a conversation."""

    role: str = Field(description="'user' or 'assistant'.")
    content: str = Field(description="The message text.")


class ChatRequest(BaseModel):
    """Inbound Copilot request from the React workspace."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Which merchants have the best autopay opportunity?",
                "conversation_id": None,
            }
        }
    )

    message: str = Field(min_length=1, max_length=2_000,
                         description="The user's natural-language question.")
    conversation_id: str | None = Field(
        default=None,
        description="Existing conversation to continue; omit to start a new one.",
    )


class ToolInvocation(BaseModel):
    """An audit record of one backend tool the Copilot executed."""

    tool: str = Field(description="Registered tool name.")
    intent: Intent = Field(description="Intent that selected the tool.")
    arguments: dict[str, Any] = Field(default_factory=dict)
    ok: bool = Field(description="Whether the tool returned successfully.")
    error: str | None = Field(default=None, description="Error message, if any.")


class CopilotResponse(BaseModel):
    """The Copilot's fully-structured answer.

    The ``executive_summary`` and ``recommended_actions`` may be phrased by
    the LLM, but every field under *evidence* is copied verbatim from the
    deterministic backend tools — the LLM never fabricates them.
    """

    conversation_id: str
    intent: Intent
    executive_summary: str = Field(description="LLM-worded headline answer.")
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Merged, raw tool outputs backing the answer.",
    )
    analytics_used: list[str] = Field(
        default_factory=list, description="Analytics facts consulted.")
    predictions_used: list[str] = Field(
        default_factory=list, description="ML predictions consulted.")
    decision: dict[str, Any] | None = Field(
        default=None, description="Decision Engine verdict, when applicable.")
    business_rules_applied: list[str] = Field(
        default_factory=list, description="Rule Engine rules that fired.")
    confidence: float | None = Field(
        default=None, description="Combined confidence [0,1], when available.")
    recommended_actions: list[str] = Field(
        default_factory=list, description="Concrete next steps.")
    tools_used: list[ToolInvocation] = Field(default_factory=list)
    referenced_entities: ReferencedEntities = Field(default_factory=ReferencedEntities)
    llm_used: bool = Field(
        default=False,
        description="True when an LLM worded the answer; False for the "
                    "deterministic fallback.",
    )


class IntentInfo(BaseModel):
    """Documentation record for one supported intent."""

    intent: Intent
    description: str
    tools: list[str]


class ToolInfo(BaseModel):
    """Documentation record for one registered tool."""

    name: str
    description: str
    intents: list[Intent]
