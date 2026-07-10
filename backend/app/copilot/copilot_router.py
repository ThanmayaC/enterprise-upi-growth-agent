"""Copilot router — the versioned HTTP surface for the AI Product Copilot.

Exposes the orchestration layer over ``/api/v1/copilot``. The router contains
no logic: it injects a request-scoped :class:`CopilotService`, hands it the
per-request SQLAlchemy session (the same ``get_db`` the rest of the platform
uses), and returns the structured :class:`CopilotResponse`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.core.dependencies import DbSession
from app.api.core.responses import ERROR_RESPONSES
from app.copilot.copilot_models import (
    ChatMessage,
    ChatRequest,
    CopilotResponse,
    IntentInfo,
    ToolInfo,
)
from app.copilot.copilot_service import CopilotService

router = APIRouter(prefix="/copilot", tags=["AI Copilot"], responses=ERROR_RESPONSES)


def get_copilot_service() -> CopilotService:
    """Provide a Copilot orchestrator (shares the process-wide conversation store)."""

    return CopilotService()


CopilotServiceDep = Annotated[CopilotService, Depends(get_copilot_service)]


@router.post("/chat", response_model=CopilotResponse, summary="Ask the Copilot")
def chat(
    request: ChatRequest, copilot: CopilotServiceDep, session: DbSession
) -> CopilotResponse:
    """Answer one natural-language question, grounded on live backend evidence."""

    return copilot.chat(request, session)


@router.get("/intents", response_model=list[IntentInfo], summary="Supported intents")
def intents(copilot: CopilotServiceDep) -> list[IntentInfo]:
    """Every intent the Copilot classifies, with its mapped tools."""

    return copilot.intents()


@router.get("/tools", response_model=list[ToolInfo], summary="Registered tools")
def tools(copilot: CopilotServiceDep) -> list[ToolInfo]:
    """Every backend tool the Copilot can orchestrate."""

    return copilot.tools()


@router.get("/suggestions", response_model=list[str], summary="Suggested questions")
def suggestions(copilot: CopilotServiceDep) -> list[str]:
    """Curated starter questions for the workspace."""

    return copilot.suggestions()


@router.get(
    "/conversations/{conversation_id}",
    response_model=list[ChatMessage],
    summary="Conversation history",
)
def conversation_history(
    conversation_id: str, copilot: CopilotServiceDep
) -> list[ChatMessage]:
    """The message history of one conversation."""

    messages = copilot.conversation_messages(conversation_id)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"conversation '{conversation_id}' does not exist",
        )
    return messages


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear a conversation",
)
def clear_conversation(conversation_id: str, copilot: CopilotServiceDep) -> None:
    """Forget a conversation's history and referenced entities."""

    if not copilot.clear_conversation(conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"conversation '{conversation_id}' does not exist",
        )
