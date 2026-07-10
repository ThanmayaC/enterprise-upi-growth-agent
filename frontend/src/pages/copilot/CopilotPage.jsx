import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, Panel, Badge } from "../../components/common/ui.jsx";
import { Spinner, ErrorState } from "../../components/common/states.jsx";
import Icon from "../../components/common/Icon.jsx";
import { useApi } from "../../hooks/useApi.js";
import { copilotApi } from "../../api/endpoints.js";

const FALLBACK_SUGGESTIONS = [
  "Give me an executive portfolio summary.",
  "Which merchants have the best autopay opportunity?",
  "Rank issuer banks by transaction success.",
  "Is merchant MER000001 eligible for autopay?",
];

const INTENT_LABEL = (v) =>
  (v || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

/** One evidence pill row: a label and its grounded sources. */
function EvidenceRow({ icon, label, items, tone = "neutral" }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="inline-flex items-center gap-1 text-xs font-medium text-ink-500">
        <Icon name={icon} size={13} className="text-ink-400" />
        {label}
      </span>
      {items.map((it, i) => (
        <Badge key={i} tone={tone}>
          {it}
        </Badge>
      ))}
    </div>
  );
}

/** The structured, grounded answer produced by the orchestration backend. */
function AnswerCard({ answer }) {
  const {
    intent,
    executive_summary,
    analytics_used,
    predictions_used,
    decision,
    business_rules_applied,
    confidence,
    recommended_actions,
    tools_used,
    llm_used,
  } = answer;

  return (
    <div className="space-y-4 rounded-2xl border border-ink-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="brand">{INTENT_LABEL(intent)}</Badge>
        {typeof confidence === "number" && (
          <Badge tone="success">Confidence {(confidence * 100).toFixed(0)}%</Badge>
        )}
        <Badge tone={llm_used ? "neutral" : "warning"}>
          {llm_used ? "LLM-worded" : "Deterministic"}
        </Badge>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">
          Executive Summary
        </p>
        <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-ink-800">
          {executive_summary}
        </p>
      </div>

      {decision && (
        <div className="rounded-xl bg-brand-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            Decision Engine
          </p>
          <p className="mt-0.5 text-sm font-semibold text-brand-800">
            {decision.decision}
          </p>
          {decision.recommended_action && (
            <p className="mt-1 text-xs text-brand-700">
              Next: {decision.recommended_action}
            </p>
          )}
        </div>
      )}

      <div className="space-y-2 border-t border-ink-100 pt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">
          Evidence
        </p>
        <EvidenceRow icon="chart" label="Analytics" items={analytics_used} tone="neutral" />
        <EvidenceRow icon="activity" label="Predictions" items={predictions_used} tone="brand" />
        <EvidenceRow
          icon="check"
          label="Business Rules"
          items={business_rules_applied}
          tone="success"
        />
        {(!analytics_used?.length &&
          !predictions_used?.length &&
          !business_rules_applied?.length) && (
          <p className="text-xs text-ink-400">
            No structured evidence was required for this answer.
          </p>
        )}
      </div>

      {recommended_actions?.length > 0 && (
        <div className="border-t border-ink-100 pt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">
            Recommended Actions
          </p>
          <ul className="mt-1 list-inside list-disc space-y-1 text-sm text-ink-700">
            {recommended_actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {tools_used?.length > 0 && (
        <details className="border-t border-ink-100 pt-3 text-xs text-ink-500">
          <summary className="cursor-pointer select-none font-medium">
            Tool trace ({tools_used.length})
          </summary>
          <div className="mt-2 space-y-1">
            {tools_used.map((t, i) => (
              <div key={i} className="flex items-center gap-2">
                <Icon
                  name={t.ok ? "check" : "alert"}
                  size={12}
                  className={t.ok ? "text-success" : "text-danger"}
                />
                <span className="font-mono">{t.tool}</span>
                {t.error && <span className="text-danger">{t.error}</span>}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

/** A single user turn. */
function UserBubble({ text }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
        {text}
      </div>
    </div>
  );
}

export default function CopilotPage() {
  const [messages, setMessages] = useState([]); // {role, ...}
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  const { data: suggestionData } = useApi(() => copilotApi.suggestions(), [], {
    cacheKey: "copilot-suggestions",
  });
  const suggestions = suggestionData?.length ? suggestionData : FALLBACK_SUGGESTIONS;

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  const send = useCallback(
    async (text) => {
      const question = (text ?? input).trim();
      if (!question || pending) return;
      setError(null);
      setInput("");
      setMessages((m) => [...m, { role: "user", text: question }]);
      setPending(true);
      try {
        const answer = await copilotApi.chat(question, conversationId);
        setConversationId(answer.conversation_id);
        setMessages((m) => [...m, { role: "assistant", answer }]);
      } catch (err) {
        setError(err);
      } finally {
        setPending(false);
      }
    },
    [input, pending, conversationId]
  );

  const clearConversation = useCallback(async () => {
    if (conversationId) {
      try {
        await copilotApi.clear(conversationId);
      } catch {
        /* already gone — ignore */
      }
    }
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, [conversationId]);

  const empty = messages.length === 0;

  return (
    <div>
      <PageHeader
        title="AI Copilot"
        description="Ask questions in natural language. Every answer is orchestrated from the analytics, ML, rule, and decision engines — never invented."
      >
        <Badge tone="brand">Phase 12</Badge>
        {!empty && (
          <button className="btn-ghost" onClick={clearConversation}>
            <Icon name="close" size={15} />
            New conversation
          </button>
        )}
      </PageHeader>

      <Panel
        title="Copilot"
        subtitle="Grounded on the Enterprise Decision Intelligence stack"
      >
        <div className="flex h-[34rem] flex-col">
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
            {empty && !pending && (
              <div className="flex h-full flex-col items-center justify-center gap-5 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
                  <Icon name="sparkles" size={30} />
                </div>
                <div>
                  <p className="text-lg font-semibold text-ink-800">
                    Your product analytics copilot
                  </p>
                  <p className="mx-auto mt-1 max-w-md text-sm text-ink-500">
                    Ask a growth question — the copilot classifies your intent, calls the
                    right backend tools, and answers with cited evidence.
                  </p>
                </div>
                <div className="flex flex-wrap justify-center gap-2">
                  {suggestions.map((q) => (
                    <button
                      key={q}
                      onClick={() => send(q)}
                      className="chip bg-ink-100 text-ink-600 transition-colors hover:bg-brand-50 hover:text-brand-700"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === "user" ? (
                <UserBubble key={i} text={m.text} />
              ) : (
                <AnswerCard key={i} answer={m.answer} />
              )
            )}

            {pending && (
              <div className="flex items-center gap-2 text-sm text-ink-500">
                <Spinner size={16} />
                Orchestrating backend tools…
              </div>
            )}

            {error && <ErrorState error={error} compact onRetry={() => send(messages.at(-1)?.text)} />}
          </div>

          <div className="border-t border-ink-100 p-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
              className="flex items-center gap-2 rounded-xl border border-ink-200 bg-white px-4 py-2.5 focus-within:border-brand-400"
            >
              <Icon name="sparkles" size={16} className="text-ink-400" />
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask the copilot anything about the portfolio…"
                disabled={pending}
                className="flex-1 bg-transparent text-sm text-ink-800 outline-none placeholder:text-ink-400"
              />
              <button
                type="submit"
                disabled={pending || !input.trim()}
                className="btn-primary disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Icon name="chevronRight" size={15} />
                Ask
              </button>
            </form>
          </div>
        </div>
      </Panel>
    </div>
  );
}
