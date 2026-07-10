"""Tool executor — runs the tools an intent selects and merges their output.

Given a classified intent and the resolved entities, the executor:

    1. asks the registry which tools are relevant,
    2. runs them in registration order against the shared service container,
    3. captures each result (or a contained error) as an audit record,
    4. merges the successful outputs into one evidence dict, tagged by tool
       *kind* so the response formatter can route facts into the correct
       structured field.

The executor is where "the AI decides which tools to call, in what order,
and merges their outputs" is realised — deterministically. It never calls the
LLM and never touches persistence; a failing tool degrades gracefully instead
of failing the whole answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.copilot.copilot_models import Intent, ReferencedEntities, ToolInvocation
from app.copilot.tool_registry import CopilotServices, Tool, ToolRegistry


@dataclass
class ExecutionResult:
    """The merged outcome of executing an intent's tools."""

    #: tool name → raw facade output (successful tools only)
    evidence: dict[str, Any] = field(default_factory=dict)
    #: tool name → tool kind ("analytics" | "prediction" | "decision" | "rule")
    kinds: dict[str, str] = field(default_factory=dict)
    #: ordered audit trail of every attempted tool
    invocations: list[ToolInvocation] = field(default_factory=list)

    def by_kind(self, kind: str) -> dict[str, Any]:
        """Successful evidence entries of a given kind."""

        return {name: self.evidence[name]
                for name, k in self.kinds.items() if k == kind}


class ToolExecutor:
    """Select, run, and merge backend tools for one classified turn."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self._registry = registry or ToolRegistry()

    def execute(
        self,
        intent: Intent,
        entities: ReferencedEntities,
        services: CopilotServices,
    ) -> ExecutionResult:
        """Run every tool the intent selects and merge the results."""

        tools = self._plan(intent)
        result = ExecutionResult()
        for tool in tools:
            self._run_one(tool, intent, entities, services, result)
        return result

    def _plan(self, intent: Intent) -> list[Tool]:
        """Choose the ordered tool set for an intent.

        Falls back to the model-catalogue tool so a general question still
        returns grounded platform facts rather than nothing.
        """

        tools = self._registry.for_intent(intent)
        if not tools:
            fallback = self._registry.get("model_catalog_tool")
            tools = [fallback] if fallback else []
        return tools

    @staticmethod
    def _run_one(
        tool: Tool,
        intent: Intent,
        entities: ReferencedEntities,
        services: CopilotServices,
        result: ExecutionResult,
    ) -> None:
        """Execute a single tool, recording success or a contained failure."""

        arguments = {k: v for k, v in entities.model_dump().items() if v}
        try:
            output = tool.run(services, entities)
        except Exception as exc:  # noqa: BLE001 — isolate tool failures
            result.invocations.append(ToolInvocation(
                tool=tool.name, intent=intent, arguments=arguments,
                ok=False, error=f"{type(exc).__name__}: {exc}",
            ))
            return
        result.evidence[tool.name] = output
        result.kinds[tool.name] = tool.kind
        result.invocations.append(ToolInvocation(
            tool=tool.name, intent=intent, arguments=arguments, ok=True,
        ))
