"""Intent classification and entity extraction for the Copilot.

Turns a free-text question into a structured :class:`Intent` plus any
entities it mentions (merchant id, customer VPA, bank, PSP). The design is
deterministic-first:

    1. A fast, transparent keyword/regex classifier handles the common case
       and always yields a defensible intent. It needs no network call and
       is trivially auditable — important for an orchestration layer.
    2. When an OpenAI key is configured, the LLM is used only to *arbitrate*
       genuinely ambiguous questions, never to invent new intents: its answer
       is validated against the known enum and discarded if out of range.

Entity extraction is regex-based and intentionally conservative — it only
claims an entity it can pattern-match with confidence, leaving the rest to
conversation context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.copilot.copilot_models import Intent, ReferencedEntities

#: Ordered (intent, keyword-set) table. Order matters twice over: it is both
#: the tie-break priority (earlier, more specific intents win equal scores)
#: and the source of truth for the docs surfaces. Keywords are matched as word
#: *prefixes* (see :meth:`_hits`) so "merchant" also covers "merchants" without
#: listing plurals — listing both would double-count a single token.
_KEYWORDS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (Intent.AUTOPAY_OPPORTUNITY,
     ("autopay", "auto pay", "mandate", "e-mandate", "recurring")),
    (Intent.GROWTH_OPPORTUNITY,
     ("growth opportunity", "opportunity", "upsell", "expansion", "grow")),
    (Intent.TRANSACTION_SUCCESS,
     ("success rate", "success probability", "will this transaction",
      "decline", "failure rate", "transaction success")),
    (Intent.DECISION_EXPLANATION,
     ("decision", "eligible", "eligibility", "approve", "retry",
      "should we", "recommend")),
    (Intent.RULE_EXPLANATION,
     ("rule", "policy", "npci", "compliance", "why was")),
    (Intent.MERCHANT_ANALYSIS,
     ("merchant", "seller", "payee")),
    (Intent.CUSTOMER_ANALYSIS,
     ("customer", "payer", "vpa", "user")),
    (Intent.BANK_ANALYSIS,
     ("bank", "issuer", "acquirer")),
    (Intent.PSP_ANALYSIS,
     ("psp", "payment service provider", "app provider")),
    (Intent.PORTFOLIO_ANALYSIS,
     ("portfolio", "overall", "overview", "total", "business health",
      "kpi", "trend")),
)

#: Only the two entity types with unambiguous, self-validating formats are
#: extracted. Bank/PSP names are free-form and would need the master list to
#: match safely, so they are resolved by the tools, not guessed from prose.
_MERCHANT_RE = re.compile(r"\bMER\d{3,}\b", re.IGNORECASE)
_VPA_RE = re.compile(r"\b[\w.\-]+@[\w.\-]+\b")

#: Words that turn an entity-scoped question into a *decision* question. When
#: one of these accompanies a concrete merchant/customer, the question must be
#: answered by the Decision Engine, never by raw analytics — this guarantees
#: the Copilot cannot bypass the Decision Engine for eligibility/approval asks.
_DECISION_TRIGGERS = (
    "eligible", "eligibility", "approve", "approved", "retry",
    "should we", "should i", "recommend", "decision",
)

#: Explicit "explain the rules/policy" phrasing must reach the Rule Engine's
#: catalogue rather than an ML opportunity model, even when other domain words
#: (e.g. "autopay") co-occur. Requires a rule word AND an explanatory verb so
#: it never hijacks genuine opportunity questions.
_RULE_WORDS = ("rule", "policy", "npci", "compliance")
_EXPLAIN_WORDS = (
    "explain", "what are", "which rules", "govern", "list", "describe",
    "tell me about", "how do", "what rules",
)


@dataclass
class Classification:
    """The outcome of classifying one message."""

    intent: Intent
    entities: ReferencedEntities
    rationale: str


class IntentClassifier:
    """Classify questions and extract referenced entities.

    Parameters:
        llm: Optional LLM client (see :mod:`response_formatter`). When
            present it is consulted only for ambiguous questions; its output
            is always validated against :class:`Intent`.
    """

    def __init__(self, llm: "object | None" = None) -> None:
        self._llm = llm

    def classify(self, message: str) -> Classification:
        """Classify a single user message."""

        entities = self._extract_entities(message)

        # Hard override: an eligibility/approval/retry question about a concrete
        # entity is a Decision Engine question, full stop.
        has_entity = bool(entities.merchant_id or entities.customer_vpa)
        lowered = message.lower()
        if has_entity and any(t in lowered for t in _DECISION_TRIGGERS):
            return Classification(
                Intent.DECISION_EXPLANATION, entities,
                "Entity + decision trigger — routed to the Decision Engine.",
            )

        # Explicit request to explain rules/policy — route to the Rule Engine.
        if (any(re.search(rf"\b{w}", lowered) for w in _RULE_WORDS)
                and any(w in lowered for w in _EXPLAIN_WORDS)):
            return Classification(
                Intent.RULE_EXPLANATION, entities,
                "Rule keyword + explanatory verb — routed to the Rule Engine.",
            )

        intent, rationale, ambiguous = self._keyword_intent(message, entities)

        if ambiguous and self._llm is not None:
            refined = self._llm_intent(message)
            if refined is not None:
                return Classification(refined, entities,
                                      "Refined by LLM arbitration.")
        return Classification(intent, entities, rationale)

    # ------------------------------------------------------------------
    # Deterministic keyword classifier
    # ------------------------------------------------------------------
    @staticmethod
    def _keyword_intent(
        message: str, entities: ReferencedEntities
    ) -> tuple[Intent, str, bool]:
        """Score intents by keyword hits; return (intent, why, ambiguous)."""

        text = message.lower()
        scores: dict[Intent, int] = {}
        for intent, words in _KEYWORDS:
            hits = sum(1 for w in words if IntentClassifier._hits(text, w))
            if hits:
                scores[intent] = hits

        # Entity mentions nudge the corresponding intent when nothing else won.
        if entities.merchant_id:
            scores[Intent.MERCHANT_ANALYSIS] = scores.get(Intent.MERCHANT_ANALYSIS, 0) + 1
        if entities.customer_vpa:
            scores[Intent.CUSTOMER_ANALYSIS] = scores.get(Intent.CUSTOMER_ANALYSIS, 0) + 1

        if not scores:
            return (Intent.GENERAL_PRODUCT_QUESTION,
                    "No domain keywords matched.", False)

        best = max(scores.values())
        winners = [i for i, s in scores.items() if s == best]
        # Preserve the priority order of the keyword table on ties.
        ordered = [i for i, _ in _KEYWORDS if i in winners]
        chosen = ordered[0]
        ambiguous = len(winners) > 1
        return (chosen,
                f"Keyword match (score={best}); "
                f"{'ambiguous, ' if ambiguous else ''}candidates="
                f"{[w.value for w in winners]}.",
                ambiguous)

    @staticmethod
    def _hits(text: str, keyword: str) -> bool:
        """Whether ``keyword`` appears as a whole word or word prefix.

        A word-boundary before the keyword prevents "user" matching inside
        "abuser"; matching a prefix (no trailing boundary) means "merchant"
        still covers "merchants" without listing the plural separately.
        """

        return re.search(rf"\b{re.escape(keyword)}", text) is not None

    # ------------------------------------------------------------------
    # Optional LLM arbitration
    # ------------------------------------------------------------------
    def _llm_intent(self, message: str) -> Intent | None:
        """Ask the LLM to pick one known intent; validate strictly."""

        labels = ", ".join(i.value for i in Intent)
        prompt = (
            "Classify the product question into exactly one of these intent "
            f"labels: {labels}. Reply with only the label.\n\nQuestion: {message}"
        )
        try:
            raw = self._llm.complete(  # type: ignore[attr-defined]
                system="You are an intent classifier. Reply with one label only.",
                user=prompt,
            ).strip().lower()
        except Exception:
            return None
        for intent in Intent:
            if intent.value in raw:
                return intent
        return None

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_entities(message: str) -> ReferencedEntities:
        """Pull merchant id / customer VPA / bank / PSP out of the text."""

        merchant = _MERCHANT_RE.search(message)
        vpa = _VPA_RE.search(message)
        return ReferencedEntities(
            merchant_id=merchant.group(0).upper() if merchant else None,
            customer_vpa=vpa.group(0) if vpa else None,
        )
