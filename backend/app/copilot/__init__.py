"""Enterprise AI Product Copilot (Phase 12).

An **orchestration layer** — not a chatbot and not a ChatGPT wrapper. It
classifies a product question, calls the existing Analytics, ML Intelligence,
Rule, and Decision facades through registered tools, and uses an LLM only to
word the grounded evidence into an executive answer. It never re-implements
platform logic and never touches the database directly.

Public surface:
    * :class:`CopilotService` — the orchestration entry point.
    * :data:`router` — the ``/api/v1/copilot`` HTTP surface.
"""

from app.copilot.copilot_router import router
from app.copilot.copilot_service import CopilotService

__all__ = ["CopilotService", "router"]
