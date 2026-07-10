"""Response formatting — deterministic assembly plus optional LLM wording.

This module produces the final :class:`CopilotResponse`. It does two jobs and
keeps them strictly separated:

    * **Deterministic assembly** — the evidence, the analytics/predictions
      used, the Decision Engine verdict, the business rules that fired, and the
      combined confidence are all extracted *from the tool outputs*, never from
      the LLM. This is the audit-grade backbone of every answer.

    * **LLM wording (optional)** — an OpenAI model turns that evidence into an
      executive summary and recommended actions. When no API key is configured
      (or the call fails) a deterministic fallback narrator is used instead, so
      the Copilot always answers and never hard-depends on the network.

The :class:`LLMClient` wraps the OpenAI SDK behind a two-method interface
(``available`` / ``complete``) so the rest of the package is provider-agnostic
and fully testable without a key.
"""

from __future__ import annotations

import json
from typing import Any

from app.copilot.copilot_models import (
    CopilotResponse,
    Intent,
    ReferencedEntities,
)
from app.copilot.tool_executor import ExecutionResult
from app.core.config import Settings


class LLMClient:
    """Thin wrapper over the OpenAI SDK with graceful absence handling.

    Parameters:
        settings: Application settings carrying the API key and model.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = self._build_client()

    def _build_client(self) -> "object | None":
        """Instantiate the OpenAI client, or ``None`` if unavailable."""

        if not self._settings.OPENAI_API_KEY:
            return None
        try:
            from openai import OpenAI  # imported lazily; optional dependency
        except Exception:
            return None
        try:
            return OpenAI(
                api_key=self._settings.OPENAI_API_KEY,
                timeout=self._settings.OPENAI_TIMEOUT,
            )
        except Exception:
            return None

    @property
    def available(self) -> bool:
        """Whether a live LLM backend is configured and importable."""

        return self._client is not None

    def complete(self, *, system: str, user: str) -> str:
        """Run one chat completion and return the raw text content."""

        if self._client is None:
            raise RuntimeError("LLM client is not configured")
        response = self._client.chat.completions.create(  # type: ignore[attr-defined]
            model=self._settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


class ResponseFormatter:
    """Build the final structured Copilot answer from executed evidence."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def format(
        self,
        *,
        conversation_id: str,
        question: str,
        intent: Intent,
        entities: ReferencedEntities,
        execution: ExecutionResult,
        system_prompt: str,
        user_prompt: str,
    ) -> CopilotResponse:
        """Assemble evidence deterministically, then word it (LLM or fallback)."""

        analytics_used = self._label_sources(execution, "analytics")
        predictions_used = self._label_sources(execution, "prediction")
        decision = self._extract_decision(execution)
        rules = self._extract_rules(decision)
        confidence = decision.get("confidence") if decision else None

        summary, actions, llm_used = self._word(
            question, decision, execution, system_prompt, user_prompt
        )

        return CopilotResponse(
            conversation_id=conversation_id,
            intent=intent,
            executive_summary=summary,
            evidence=execution.evidence,
            analytics_used=analytics_used,
            predictions_used=predictions_used,
            decision=decision,
            business_rules_applied=rules,
            confidence=confidence,
            recommended_actions=actions,
            tools_used=execution.invocations,
            referenced_entities=entities,
            llm_used=llm_used,
        )

    # ------------------------------------------------------------------
    # Deterministic evidence extraction (never from the LLM)
    # ------------------------------------------------------------------
    @staticmethod
    def _label_sources(execution: ExecutionResult, kind: str) -> list[str]:
        """Human-readable list of the tool outputs of a given kind."""

        labels: list[str] = []
        for name, data in execution.by_kind(kind).items():
            keys = list(data.keys()) if isinstance(data, dict) else []
            labels.append(f"{name}: {', '.join(keys)}" if keys else name)
        return labels

    @staticmethod
    def _extract_decision(execution: ExecutionResult) -> dict[str, Any] | None:
        """Pull the single most-relevant Decision Engine verdict, if any.

        Decision tools return one or more ``DecisionResult`` dicts; we surface
        the first fully-formed verdict (one carrying a ``decision`` label).
        """

        for data in execution.by_kind("decision").values():
            if not isinstance(data, dict):
                continue
            for value in data.values():
                if isinstance(value, dict) and "decision" in value:
                    return value
        return None

    @staticmethod
    def _extract_rules(decision: dict[str, Any] | None) -> list[str]:
        """Names of the rules that fired inside a decision result."""

        if not decision:
            return []
        results = decision.get("rule_results", [])
        return [r.get("rule_name", "unknown")
                for r in results if isinstance(r, dict)]

    # ------------------------------------------------------------------
    # Wording — LLM when available, deterministic fallback otherwise
    # ------------------------------------------------------------------
    def _word(
        self,
        question: str,
        decision: dict[str, Any] | None,
        execution: ExecutionResult,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, list[str], bool]:
        """Return (executive_summary, recommended_actions, llm_used)."""

        if self._llm.available:
            try:
                raw = self._llm.complete(system=system_prompt, user=user_prompt)
                summary, actions = self._parse_llm(raw)
                if summary:
                    return summary, actions, True
            except Exception:
                pass  # fall through to deterministic narrator
        summary, actions = self._fallback(question, decision, execution)
        return summary, actions, False

    @staticmethod
    def _parse_llm(raw: str) -> tuple[str, list[str]]:
        """Parse the model's JSON reply, tolerating fenced code blocks."""

        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("{"):]
        try:
            payload = json.loads(text)
        except Exception:
            return raw.strip(), []
        summary = str(payload.get("executive_summary", "")).strip()
        actions = payload.get("recommended_actions", [])
        if not isinstance(actions, list):
            actions = [str(actions)]
        return summary, [str(a) for a in actions]

    @staticmethod
    def _fallback(
        question: str,
        decision: dict[str, Any] | None,
        execution: ExecutionResult,
    ) -> tuple[str, list[str]]:
        """Deterministic narrator used when no LLM is available.

        It reports which grounded sources answered the question and echoes the
        Decision Engine's own reasoning/action verbatim — inventing nothing.
        """

        sources = ", ".join(execution.evidence.keys()) or "no tools"
        if decision:
            reasons = "; ".join(decision.get("business_reasons", [])) or "n/a"
            summary = (
                f"Decision '{decision.get('decision')}' for "
                f"{decision.get('subject', {})} "
                f"(confidence {decision.get('confidence')}). Basis: {reasons}."
            )
            action = decision.get("recommended_action")
            return summary, [action] if action else []

        summary = (
            f"Grounded on {sources}. The evidence panel contains the analytics "
            f"and predictions consulted for: \"{question}\". "
            "Configure OPENAI_API_KEY for a narrated executive summary."
        )
        return summary, []
