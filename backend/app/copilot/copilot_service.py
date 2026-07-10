"""CopilotService — the Phase-12 orchestration entry point.

Wires the Copilot pipeline end-to-end for a single turn:

    classify → resolve entities from conversation → execute backend tools →
    build grounded prompt → word the answer → update conversation → return.

It owns no business logic of its own: intent routing, tool execution, and
wording each live in their dedicated collaborators, and every fact comes from
the frozen Analytics / ML / Decision facades via :class:`CopilotServices`.
This class only sequences them.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.copilot.conversation import ConversationStore
from app.copilot.copilot_models import (
    ChatRequest,
    CopilotResponse,
    Intent,
    IntentInfo,
    ToolInfo,
)
from app.copilot.intent_classifier import IntentClassifier
from app.copilot.prompt_builder import build_system_prompt, build_user_prompt
from app.copilot.response_formatter import LLMClient, ResponseFormatter
from app.copilot.tool_registry import CopilotServices, ToolRegistry
from app.copilot.tool_executor import ToolExecutor
from app.core.config import Settings, get_settings

#: One-line documentation per intent, surfaced by ``/copilot/intents``.
_INTENT_DOCS = {
    "portfolio_analysis": "Executive portfolio KPIs, growth, and health.",
    "merchant_analysis": "Merchant profiles, rankings, and success rates.",
    "customer_analysis": "Customer activity, top customers, lifetime value.",
    "bank_analysis": "Issuer/acquirer rankings and analysis.",
    "psp_analysis": "PSP rankings, performance, and success analysis.",
    "growth_opportunity": "ML-ranked merchant growth opportunities.",
    "autopay_opportunity": "ML-ranked autopay adoption opportunities.",
    "transaction_success": "Transaction success-probability model.",
    "decision_explanation": "Decision Engine verdicts and their basis.",
    "rule_explanation": "Business-rule catalogue and NPCI configuration.",
    "general_product_question": "Grounded platform facts and model catalogue.",
}

#: Curated starter questions for the workspace's suggestion chips.
_SUGGESTIONS = [
    "Give me an executive portfolio summary.",
    "Which merchants have the best autopay opportunity?",
    "Rank issuer banks by transaction success.",
    "Is merchant MER000001 eligible for autopay?",
    "Explain the business rules that govern autopay eligibility.",
    "Which merchants are predicted to grow the most?",
]


class CopilotService:
    """Sequence the Copilot pipeline for a conversation turn.

    Parameters:
        settings: Application settings (LLM config, feature flag).
        store: Shared conversation store (process-lifetime singleton).
        registry: Tool catalogue (defaults to the built-in registry).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        store: ConversationStore | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._store = store or _SHARED_STORE
        self._registry = registry or ToolRegistry()
        self._llm = LLMClient(self._settings)
        self._classifier = IntentClassifier(llm=self._llm if self._llm.available else None)
        self._executor = ToolExecutor(self._registry)
        self._formatter = ResponseFormatter(self._llm)

    # ------------------------------------------------------------------
    # Main turn
    # ------------------------------------------------------------------
    def chat(self, request: ChatRequest, session: Session) -> CopilotResponse:
        """Answer one user message, grounded on live backend evidence."""

        conversation = self._store.get_or_create(request.conversation_id)
        conversation.add_user(request.message)

        classification = self._classifier.classify(request.message)
        # Merge freshly-mentioned entities over the carried-forward context so
        # follow-ups resolve against the last-referenced subject.
        entities = conversation.remember(classification.entities)

        services = CopilotServices(session)
        execution = self._executor.execute(
            classification.intent, entities, services
        )

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(
            question=request.message,
            intent=classification.intent,
            entities=entities,
            execution=execution,
            conversation=conversation,
        )

        response = self._formatter.format(
            conversation_id=conversation.conversation_id,
            question=request.message,
            intent=classification.intent,
            entities=entities,
            execution=execution,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        conversation.add_assistant(response.executive_summary)
        return response

    # ------------------------------------------------------------------
    # Documentation / introspection surfaces
    # ------------------------------------------------------------------
    def intents(self) -> list[IntentInfo]:
        """Every supported intent with its description and mapped tools."""

        return [
            IntentInfo(
                intent=intent,
                description=_INTENT_DOCS.get(intent.value, ""),
                tools=[t.name for t in self._registry.for_intent(intent)],
            )
            for intent in Intent
        ]

    def tools(self) -> list[ToolInfo]:
        """Every registered tool and the intents it serves."""

        return [
            ToolInfo(name=t.name, description=t.description,
                     intents=list(t.intents))
            for t in self._registry.all()
        ]

    @staticmethod
    def suggestions() -> list[str]:
        """Starter questions for the workspace."""

        return list(_SUGGESTIONS)

    def conversation_messages(self, conversation_id: str):
        """Return a conversation's message history, or ``None``."""

        conversation = self._store.get(conversation_id)
        return conversation.messages if conversation else None

    def clear_conversation(self, conversation_id: str) -> bool:
        """Forget a conversation."""

        return self._store.delete(conversation_id)


#: Process-lifetime conversation store shared across requests. Phase 12 is
#: single-process and stateless-per-request otherwise; this is the one piece
#: of intentional in-memory state (see :class:`ConversationStore`).
_SHARED_STORE = ConversationStore()
