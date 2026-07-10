"""Prompt construction for the Copilot's LLM wording step.

Builds the system and user prompts that turn deterministic backend evidence
into a professional, grounded answer. The single most important contract is
enforced here: **the LLM may only summarise, explain, and phrase — it must
never invent analytics, predictions, decisions, or rules.** The system prompt
states this explicitly and the user prompt hands the model *only* the evidence
the tools produced, plus recent conversation context.

Raw database rows never appear: tools already return service-shaped DTOs, and
we serialise those compactly, truncating large collections so the prompt stays
within budget without hiding which facts were used.
"""

from __future__ import annotations

import json
from typing import Any

from app.copilot.conversation import Conversation
from app.copilot.copilot_models import Intent, ReferencedEntities
from app.copilot.tool_executor import ExecutionResult

_SYSTEM_PROMPT = (
    "You are the Enterprise UPI Growth Copilot, an orchestration layer over a "
    "deterministic analytics, ML, rule, and decision platform.\n\n"
    "STRICT RULES:\n"
    "1. Use ONLY the EVIDENCE provided. Never invent numbers, predictions, "
    "decisions, or business rules.\n"
    "2. If the evidence does not answer the question, say so plainly.\n"
    "3. You may summarise, explain, compare, and word professionally — nothing "
    "more.\n"
    "4. Attribute facts to their source (Analytics, ML prediction, Decision "
    "Engine, or Rule Engine).\n"
    "5. Be concise and executive in tone.\n\n"
    "Respond as a JSON object with keys: executive_summary (string), "
    "recommended_actions (array of strings)."
)

#: Cap on list length embedded per evidence branch — keeps prompts bounded
#: while still showing the model what was consulted.
_MAX_LIST = 8


def build_system_prompt() -> str:
    """The invariant system prompt enforcing the grounding contract."""

    return _SYSTEM_PROMPT


def build_user_prompt(
    *,
    question: str,
    intent: Intent,
    entities: ReferencedEntities,
    execution: ExecutionResult,
    conversation: Conversation,
) -> str:
    """Assemble the user prompt from question, context, and evidence."""

    context = _conversation_context(conversation)
    evidence = _render_evidence(execution)
    entity_line = ", ".join(
        f"{k}={v}" for k, v in entities.model_dump().items() if v
    ) or "none"

    return (
        f"USER QUESTION:\n{question}\n\n"
        f"DETECTED INTENT: {intent.value}\n"
        f"REFERENCED ENTITIES: {entity_line}\n\n"
        f"CONVERSATION CONTEXT:\n{context or '(none)'}\n\n"
        f"EVIDENCE (grounded backend facts — use only these):\n{evidence}\n\n"
        "Write the executive_summary and recommended_actions grounded strictly "
        "in the evidence above."
    )


def _conversation_context(conversation: Conversation) -> str:
    """Render the last few turns as a compact transcript."""

    lines = [f"{m.role}: {m.content}" for m in conversation.recent()]
    return "\n".join(lines)


def _render_evidence(execution: ExecutionResult) -> str:
    """Serialise merged tool output compactly, grouped by source kind."""

    if not execution.evidence:
        return "(no backend evidence was produced)"

    grouped: dict[str, dict[str, Any]] = {}
    for name, kind in execution.kinds.items():
        grouped.setdefault(kind, {})[name] = _truncate(execution.evidence[name])

    return json.dumps(grouped, default=str, indent=2)


def _truncate(value: Any) -> Any:
    """Recursively bound list sizes so the prompt cannot blow up."""

    if isinstance(value, dict):
        return {k: _truncate(v) for k, v in value.items()}
    if isinstance(value, list):
        clipped = [_truncate(v) for v in value[:_MAX_LIST]]
        if len(value) > _MAX_LIST:
            clipped.append(f"... (+{len(value) - _MAX_LIST} more)")
        return clipped
    return value
