"""Conversation state for the AI Product Copilot.

Maintains, per conversation:

    * the ordered message history (for LLM context and the UI),
    * the entities the dialogue is anchored to (last-referenced merchant,
      customer, bank, PSP), so follow-up questions resolve naturally.

This is an in-process store — deliberately simple, since Phase 12 excludes
authentication and persistence. It is thread-agnostic and keyed by an opaque
conversation id. Swapping it for Redis later means re-implementing the same
small interface, nothing else.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.copilot.copilot_models import ChatMessage, ReferencedEntities


@dataclass
class Conversation:
    """A single Copilot dialogue and its accumulated context."""

    conversation_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    entities: ReferencedEntities = field(default_factory=ReferencedEntities)

    def add_user(self, content: str) -> None:
        """Append a user turn."""

        self.messages.append(ChatMessage(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        """Append an assistant turn."""

        self.messages.append(ChatMessage(role="assistant", content=content))

    def remember(self, updates: ReferencedEntities) -> ReferencedEntities:
        """Merge newly-mentioned entities over the carried-forward context.

        Only non-null fields overwrite; this is what lets "and its success
        rate?" keep pointing at the merchant named two turns ago.
        """

        merged = self.entities.model_copy(
            update={k: v for k, v in updates.model_dump().items() if v is not None}
        )
        self.entities = merged
        return merged

    def recent(self, limit: int = 6) -> list[ChatMessage]:
        """The last ``limit`` turns, oldest first — the LLM context window."""

        return self.messages[-limit:]


class ConversationStore:
    """In-memory registry of active conversations."""

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}

    def get_or_create(self, conversation_id: str | None) -> Conversation:
        """Return an existing conversation or start a fresh one.

        Unknown ids (e.g. after a server restart) transparently start a new
        conversation rather than erroring, so the UI never dead-ends.
        """

        if conversation_id and conversation_id in self._conversations:
            return self._conversations[conversation_id]
        new_id = conversation_id or uuid.uuid4().hex
        conversation = Conversation(conversation_id=new_id)
        self._conversations[new_id] = conversation
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        """Look up a conversation without creating one."""

        return self._conversations.get(conversation_id)

    def delete(self, conversation_id: str) -> bool:
        """Forget a conversation; returns whether one was removed."""

        return self._conversations.pop(conversation_id, None) is not None
