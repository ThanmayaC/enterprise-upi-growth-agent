# Enterprise UPI Growth Intelligence Platform

## Product Design Specification v1.0

> **"Transforming UPI Ecosystem Data into Product Intelligence"**

| | |
|---|---|
| **Document** | Master Product Design Document (Single Source of Truth) |
| **Version** | 1.0 |
| **Status** | Approved Baseline |
| **Date** | 08 July 2026 |
| **Classification** | Internal — NPCI |
| **Related Documents** | Database Architecture v1.0 (Frozen), Backend Foundation README |

---

## Table of Contents

1. [Vision, Mission, Goals & Non-Goals](#1-vision-mission-goals--non-goals)
2. [Problem Statement](#2-problem-statement)
3. [Target Users](#3-target-users)
4. [Product Philosophy](#4-product-philosophy)
5. [Complete Product Architecture](#5-complete-product-architecture)
6. [Core Platform Modules](#6-core-platform-modules)
7. [Module Specifications](#6-core-platform-modules)
8. [Complete User Journey](#8-complete-user-journey)
9. [Complete Feature List & Prioritization](#9-complete-feature-list--prioritization)
10. [Functional Requirements](#10-functional-requirements)
11. [Non-Functional Requirements](#11-non-functional-requirements)
12. [System Architecture](#12-system-architecture)
13. [Technology Stack](#13-technology-stack)
14. [Database Overview](#14-database-overview)
15. [Analytics Architecture](#15-analytics-architecture)
16. [Machine Learning Architecture](#16-machine-learning-architecture)
17. [Recommendation Architecture](#17-recommendation-architecture)
18. [Report Generation Architecture](#18-report-generation-architecture)
19. [AI Assistant Architecture](#19-ai-assistant-architecture)
20. [Implementation Roadmap](#20-implementation-roadmap)
21. [Success Metrics](#21-success-metrics)
22. [Future Vision](#22-future-vision)

---

## 1. Vision, Mission, Goals & Non-Goals

### 1.1 Vision

To become the **decision brain of the UPI ecosystem** — a single enterprise platform where every product decision at NPCI begins, is validated, and is communicated. The platform elevates raw transaction telemetry into strategic product intelligence, so that decisions that today take weeks of manual analysis take minutes of guided exploration.

### 1.2 Mission

Enable NPCI Product Managers to:

- **Understand** ecosystem performance across banks, PSPs, merchants, geographies, and payment instruments.
- **Detect** business opportunities hidden in transaction patterns before competitors or market forces surface them.
- **Predict** future transaction volumes, failure trends, and adoption curves with quantified confidence.
- **Receive** AI-assisted, explainable recommendations ranked by business impact.
- **Generate** executive-grade reports without manual assembly.
- **Simulate** business scenarios ("what if PSP X improves success rate by 2%?") before committing resources.
- **Decide** strategically, with every insight traceable back to the underlying data.

### 1.3 Goals

| # | Goal | Measure |
|---|------|---------|
| G1 | Reduce time-to-insight for PM questions from days to under 5 minutes | Median query-to-answer time |
| G2 | Make every metric explainable down to the transaction level | 100% of KPIs drill-down enabled |
| G3 | Provide forward-looking intelligence, not just retrospective dashboards | Forecasts available for all core KPIs |
| G4 | Convert insights into ranked, actionable recommendations | ≥ 80% of surfaced insights carry a recommended action |
| G5 | Eliminate manual executive report assembly | 1-click report generation for weekly/monthly/quarterly cycles |
| G6 | Build institutional memory of decisions and their outcomes | All decisions logged and outcome-tracked in the Strategy Workspace |

### 1.4 Non-Goals

The platform explicitly does **not** attempt to:

- **Process live payment traffic.** It is an analytical system operating on ingested transaction data, not part of the UPI switch or settlement path.
- **Replace human judgment.** Recommendations are decision support; final authority rests with Product Managers and Leadership.
- **Serve external parties.** This is an internal NPCI platform; banks, PSPs, and merchants are subjects of analysis, not users.
- **Perform fraud adjudication or compliance enforcement.** Anomaly signals may be surfaced, but fraud/risk case management belongs to dedicated systems.
- **Redesign frozen foundations.** The Database Architecture v1.0 and the backend Clean Architecture foundation are fixed inputs to this design, not outputs of it.

---

## 2. Problem Statement

UPI processes billions of transactions per month across hundreds of banks, dozens of PSP applications, and millions of merchants. The data exists — but the intelligence does not.

**Today's reality for an NPCI Product Manager:**

1. **Fragmented visibility.** Performance data lives in scattered extracts, spreadsheets, and ad-hoc SQL pulls. There is no single, trusted view of ecosystem health.
2. **Retrospective-only analysis.** Reporting answers *what happened last month*. Nobody systematically answers *what will happen next quarter* or *what should we do about it*.
3. **Opportunity blindness.** Underpenetrated merchant categories, declining PSP corridors, emerging usage patterns, and geography-level whitespace are discovered late — usually after the trend is already visible in headline numbers.
4. **Manual reporting burden.** Executive reviews consume days of analyst time assembling slides that are outdated by the time they are presented.
5. **Unexplainable numbers.** When a metric moves, tracing *why* requires manual forensic work across dimensions (bank × PSP × MCC × geography × error code).
6. **No simulation capability.** Strategic questions — "What is the volume impact if we onboard 50,000 merchants in Tier-3 cities?" — are answered by intuition, not models.
7. **Lost institutional memory.** Decisions, their rationale, and their outcomes are not systematically captured, so the organization repeats analyses and re-litigates settled questions.

**The consequence:** the world's largest real-time payments ecosystem is managed with tooling that lags its own scale. Decisions are slower, less confident, and less data-grounded than the underlying data permits.

**The solution:** an Enterprise Product Intelligence Platform that unifies descriptive, diagnostic, predictive, and prescriptive analytics — with AI assistance, explainability, and executive communication built in as first-class capabilities.

---

## 3. Target Users

### 3.1 NPCI Product Managers (Primary Persona)

| Attribute | Description |
|---|---|
| **Who** | Owners of UPI product lines — P2P, P2M, Autopay/mandates, international corridors, feature initiatives |
| **Needs** | Trend visibility, root-cause diagnosis, opportunity discovery, scenario evaluation, decision justification |
| **Pain today** | Days spent waiting on analyst pulls; no forward view; manual deck-building |
| **Platform usage** | Daily driver — dashboards, analytics deep-dives, recommendations, AI assistant, strategy workspace |
| **Success looks like** | Answers any product question in minutes; walks into reviews with pre-generated, explainable evidence |

### 3.2 Business Teams (Growth, Partnerships, Merchant Ecosystem)

| Attribute | Description |
|---|---|
| **Who** | Teams managing bank/PSP relationships, merchant category expansion, and adoption programs |
| **Needs** | Partner-level scorecards, category penetration views, campaign impact measurement |
| **Platform usage** | Weekly — entity comparisons, opportunity lists, exportable partner reviews |
| **Success looks like** | Data-backed partner conversations; prioritized target lists for merchant and geography expansion |

### 3.3 Leadership (CPO, Business Heads, Executive Committee)

| Attribute | Description |
|---|---|
| **Who** | Executives accountable for UPI growth, reliability, and strategic direction |
| **Needs** | At-a-glance ecosystem health, forecast confidence, top risks and opportunities, board-ready narratives |
| **Platform usage** | Weekly/monthly — executive dashboard, generated reports, scenario outcomes |
| **Success looks like** | Trustworthy single source of truth; every number in a board deck traceable to the platform |

### 3.4 Operations & Analytics Teams

| Attribute | Description |
|---|---|
| **Who** | Teams monitoring transaction success health, data pipelines, and platform administration |
| **Needs** | Failure diagnostics by bank/PSP/error-code, anomaly alerts, data-quality assurance, user and access management |
| **Platform usage** | Daily — failure analytics, anomaly feeds, admin console, pipeline health |
| **Success looks like** | Degradations detected from data patterns before they become escalations; clean, trusted data feeding all modules |

---

## 4. Product Philosophy

Every module in the platform is designed around **seven canonical questions**. A module is complete only when it can answer all questions relevant to its scope:

| # | Question | Intelligence Layer | Primary Modules |
|---|----------|-------------------|-----------------|
| 1 | **What happened?** | Descriptive | Executive Dashboard, Analytics Engine |
| 2 | **Why did it happen?** | Diagnostic | Analytics Engine, Explainability & Trust Engine |
| 3 | **What will happen?** | Predictive | Predictive Intelligence Engine |
| 4 | **What should we do?** | Prescriptive | Recommendation Engine |
| 5 | **What opportunity are we missing?** | Discovery | Opportunity Discovery Engine |
| 6 | **What if?** | Simulative | Scenario Simulation Engine |
| 7 | **How do we communicate this?** | Narrative | Report Generation Engine, AI Growth Assistant |

**Design principles derived from this philosophy:**

1. **Insight over data.** No screen ships raw numbers without context — every metric carries trend, benchmark, and significance.
2. **Explainability is non-negotiable.** Any number, forecast, or recommendation can be interrogated: *"show me why."*
3. **Prescriptive by default.** Where the platform detects a problem or opportunity, it proposes an action.
4. **Narrative-ready.** Every view is one step away from an executive-consumable artifact.
5. **Trust through transparency.** Model confidence, data freshness, and lineage are always visible.
6. **PM workflow, not analyst workflow.** The primary user writes product strategy, not SQL.

---

## 5. Complete Product Architecture

The platform is organized into **five horizontal layers** and **twelve vertical modules**.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        EXPERIENCE LAYER                                    │
│  Executive Dashboard │ Analytics Workbench │ Strategy Workspace │ Reports  │
│  AI Growth Assistant │ Knowledge Hub       │ Admin Console                 │
├────────────────────────────────────────────────────────────────────────────┤
│                        INTELLIGENCE LAYER                                  │
│  Predictive Engine │ Recommendation Engine │ Opportunity Discovery         │
│  Scenario Simulation │ Explainability & Trust │ Report Generation          │
├────────────────────────────────────────────────────────────────────────────┤
│                        ANALYTICS LAYER                                     │
│  Enterprise Analytics Engine: KPI computation, aggregation services,       │
│  dimensional analysis, cohort & funnel analysis, anomaly statistics        │
├────────────────────────────────────────────────────────────────────────────┤
│                        SERVICE / API LAYER  (Frozen Backend Foundation)    │
│  FastAPI application • Clean Architecture:                                 │
│  api → services → repositories → models • Pydantic schemas • Auth          │
├────────────────────────────────────────────────────────────────────────────┤
│                        DATA LAYER  (Frozen — Database Architecture v1.0)   │
│  PostgreSQL • Transaction fact store • Master/dimension data •             │
│  Aggregate tables • Alembic migrations                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

**Architectural rules:**

- The Experience Layer never queries the database directly; all access flows through the Service/API Layer.
- The Intelligence Layer consumes outputs of the Analytics Layer — it never re-implements KPI logic.
- The Analytics Layer is the **single source of metric truth**: one definition of "success rate," used everywhere.
- The Data Layer and Service Layer foundations are **frozen**; all new modules extend them via the established layering (routers → services → repositories), never bypass them.

---

## 6. Core Platform Modules

### 6.1 Executive Intelligence Dashboard

**Purpose.** The command center — a single screen that tells any stakeholder, in under 30 seconds, whether the UPI ecosystem is healthy, where it is heading, and what needs attention today.

**Inputs.**
- Pre-computed KPI aggregates from the Analytics Engine (volume, value, success rate, active entities)
- Forecast overlays from the Predictive Engine
- Top-ranked alerts from Opportunity Discovery and anomaly detection
- User role and preferences (which KPIs are pinned)

**Outputs.**
- KPI scorecards with period-over-period deltas and trend sparklines
- Ecosystem health composite score
- "Attention feed": top anomalies, risks, and opportunities ranked by impact
- Drill-down navigation into the Analytics Engine

**Features.**
- Time-window control (day/week/month/quarter/custom) applied globally
- KPI cards: transaction volume, transaction value, success rate, failure rate, active banks/PSPs/merchants, average ticket size, P2P vs P2M mix
- Trend visualization with forecast continuation (actuals + predicted band on one chart)
- Geographic heat view of transaction intensity and growth
- Leaderboards: top/bottom banks and PSPs by success rate and growth
- Configurable layout per role (PM view vs Leadership view)
- Alert badges with one-click "explain this" routed to the Explainability Engine

**User stories.**
- *As a CPO, I want a single health score with supporting KPIs so that I can assess the ecosystem in my first minute of the day.*
- *As a PM, I want week-over-week deltas with significance markers so that I don't chase noise.*
- *As a business head, I want the top 5 things needing attention today, ranked by business impact, so that my team's focus is data-driven.*
- *As an operations lead, I want failure-rate spikes surfaced with the responsible dimension (bank/PSP/error code) so that I can escalate precisely.*

**Business value.** Replaces dispersed spreadsheets with one trusted view; compresses executive situational awareness from hours to seconds; ensures the whole organization argues from the same numbers.

**Future scope.** Real-time streaming tiles; personalized "morning briefing" push; TV/wallboard mode for operations floors; mobile executive app.

---

### 6.2 Enterprise Analytics Engine

**Purpose.** The analytical backbone. Computes every KPI once, consistently, and exposes multidimensional exploration — the module that answers *what happened* and, through guided decomposition, *why*.

**Inputs.**
- Transaction fact data and master/dimension data per Database Architecture v1.0 (transaction type, timestamps, payer/payee banks and PSPs, merchant category codes, amounts, initiation modes, response/error codes, mandate attributes)
- Pre-built aggregate tables for high-frequency query paths
- Metric definitions from the governed KPI dictionary

**Outputs.**
- KPI values with full dimensional slicing (time × bank × PSP × merchant category × transaction type × geography × initiation mode × error code)
- Trend series, growth rates (DoD/WoW/MoM/QoQ/YoY), moving averages
- Contribution and variance decomposition ("success rate fell 0.4%; 70% of the decline traces to Bank X timeout errors")
- Cohort and funnel outputs (merchant activation cohorts, mandate lifecycle funnels)

**Features.**
- Governed KPI dictionary — one definition per metric, versioned, documented
- Slice-and-dice explorer: any KPI by any dimension combination with instant pivot
- Comparative analysis: entity vs entity, period vs period, segment vs segment
- Failure analytics suite: error-code Pareto, failure heatmap by bank × PSP, timeout vs business-decline split
- Merchant analytics: category (MCC) performance, onboarding-type analysis, merchant genre trends
- Mandate/Autopay analytics: creation, execution, revocation funnels
- Statistical rigor: significance testing on deltas, seasonality-adjusted comparisons
- Saved analyses and shareable analysis links

**User stories.**
- *As a PM, I want to decompose a success-rate drop across bank, PSP, and error code in one view so that I find the root cause without writing SQL.*
- *As a business team member, I want MCC-level volume trends so that I can identify which merchant categories are accelerating.*
- *As an analyst, I want every KPI to have a single governed definition so that two teams never present two versions of "success rate."*
- *As a PM, I want mandate execution funnels so that I can quantify Autopay drop-off points.*

**Business value.** Establishes the single source of metric truth; converts multi-day analyst investigations into self-service minutes; the foundation every other intelligence module builds on.

**Future scope.** Natural-language query translation (delegated to AI Assistant); automated insight narration on every chart; user-defined custom metrics with governance workflow.

---

### 6.3 Predictive Intelligence Engine

**Purpose.** Answers *what will happen*. Produces forecasts and early-warning signals for core ecosystem KPIs with quantified uncertainty.

**Inputs.**
- Historical KPI time series from the Analytics Engine (never raw recomputation)
- Calendar features: festivals, salary cycles, month-end effects, weekday patterns
- Entity metadata for segment-level models (bank tier, PSP scale, MCC group)

**Outputs.**
- Volume, value, and success-rate forecasts at ecosystem, bank, PSP, and category level (daily/weekly/monthly horizons)
- Prediction intervals (e.g., P10/P50/P90 bands) on every forecast
- Trend-change and inflection alerts ("PSP X growth decelerating; projected to turn negative within 6 weeks")
- Anomaly probability scores feeding the Dashboard attention feed
- Model performance metadata (backtest accuracy, last training date) for the Trust Engine

**Features.**
- Multi-horizon forecasting (7/30/90 day) for all core KPIs
- Segment-level forecasts: per bank, per PSP, per merchant category
- Seasonality decomposition views (trend / weekly / festival effects)
- Early-warning system: forecasted breaches of health thresholds
- Champion/challenger model management with automatic backtesting
- Forecast vs actual tracking with visible accuracy history

**User stories.**
- *As a leadership member, I want next quarter's volume forecast with confidence bands so that I can set realistic targets.*
- *As a PM, I want alerts when an entity's trajectory is predicted to breach a health threshold so that I intervene before the decline is visible in monthly numbers.*
- *As an analyst, I want forecast accuracy history so that I can calibrate how much to trust each model.*

**Business value.** Shifts the organization from reactive to anticipatory management; makes target-setting and capacity planning evidence-based; provides the quantitative substrate for recommendations and simulations.

**Future scope.** External signal enrichment (macro indicators, smartphone penetration); hierarchical reconciliation (entity forecasts summing consistently to ecosystem totals); probabilistic event modeling for regulatory or pricing changes.

---

### 6.4 Recommendation Engine

**Purpose.** Answers *what should we do*. Converts analytical findings and predictions into a ranked queue of concrete, explainable actions with estimated impact.

**Inputs.**
- Diagnostic outputs from the Analytics Engine (root-caused problems)
- Forecasts and early warnings from the Predictive Engine
- Opportunity candidates from the Opportunity Discovery Engine
- Business rule library (thresholds, playbooks, strategic priorities set by admins)
- Historical recommendation outcomes (accepted/rejected/impact realized)

**Outputs.**
- Ranked recommendation cards: *action, target entity, rationale, estimated impact, confidence, urgency*
- Recommendation categories: reliability improvement, growth acceleration, partner intervention, category expansion, experience optimization
- Impact estimates in business units (transactions/month, success-rate basis points)
- Full evidence chain per recommendation (via Explainability Engine)

**Features.**
- Impact-based ranking (expected value × confidence × strategic weight)
- Recommendation lifecycle: proposed → under review → accepted → in execution → outcome measured → closed
- One-click "send to Strategy Workspace" to convert a recommendation into an initiative
- Feedback capture: accept/reject with reason, feeding future ranking
- Playbook templates: recurring recommendation patterns (e.g., "PSP success-rate remediation") with standard action steps
- Duplicate/conflict detection across recommendations

**User stories.**
- *As a PM, I want a prioritized list of the highest-impact actions for my product line so that my roadmap starts from evidence rather than intuition.*
- *As a business team member, I want partner-intervention recommendations with the supporting data pre-assembled so that partner conversations are immediately actionable.*
- *As a leadership member, I want to see the pipeline of accepted recommendations and their measured outcomes so that I can judge the platform's real impact.*

**Business value.** Closes the insight-to-action gap — the point where most analytics platforms fail; creates an auditable link between data, decision, and outcome; compounds in value as outcome feedback improves ranking.

**Future scope.** Reinforcement-style ranking tuned on realized outcomes; recommendation bundling into coherent strategic programs; cross-PM coordination detection ("three teams are independently targeting the same banks").

---

### 6.5 Opportunity Discovery Engine

**Purpose.** Answers *what opportunity are we missing*. Proactively scans the ecosystem for whitespace, underperformance gaps, and emerging patterns that no one asked about.

**Inputs.**
- Full dimensional aggregates from the Analytics Engine
- Benchmark models (expected performance by peer group: similar banks, similar MCCs, similar geographies)
- Growth trajectories from the Predictive Engine
- Discovery rule library and statistical pattern miners

**Outputs.**
- Opportunity cards: *type, entities involved, size estimate, evidence, suggested next step*
- Opportunity types: **gap** (entity underperforming its peer benchmark), **whitespace** (underpenetrated MCC/geography combinations), **momentum** (emerging pattern worth amplifying), **at-risk** (value that will be lost without intervention)
- Sized opportunity backlog, sortable by estimated value

**Features.**
- Peer benchmarking: every entity scored against its statistical peer group, gaps quantified
- Whitespace mapping: MCC × geography matrix of penetration vs potential
- Emerging-pattern detection: statistically unusual growth pockets surfaced automatically
- Momentum tracking: which categories/corridors are inflecting upward
- Opportunity sizing: transaction and value potential using benchmark closure assumptions
- Watchlists: follow an opportunity and get notified as evidence strengthens
- Scheduled discovery sweeps with digest notifications

**User stories.**
- *As a PM, I want to see which merchant categories are underpenetrated relative to comparable categories so that I can target expansion where headroom is largest.*
- *As a business team member, I want a ranked list of banks performing below their peer benchmark so that partnership effort goes where the recoverable value is highest.*
- *As a leadership member, I want a quarterly "missed opportunity" review so that strategic planning starts from quantified whitespace.*

**Business value.** Converts the platform from a question-answering tool into a question-asking tool; systematically surfaces growth that would otherwise be found late or never; feeds a continuously sized opportunity backlog into strategic planning.

**Future scope.** Competitive-context enrichment; opportunity clustering into strategic themes; automatic pairing of each opportunity with a simulated intervention scenario.

---

### 6.6 Scenario Simulation Engine

**Purpose.** Answers *what if*. Lets PMs and leadership test strategic hypotheticals against models before committing real-world resources.

**Inputs.**
- Baseline forecasts from the Predictive Intelligence Engine
- User-defined scenario parameters (lever, magnitude, timing, duration, affected entities)
- Elasticity and relationship models learned from historical data (e.g., historical relationship between success-rate improvements and volume retention)

**Outputs.**
- Scenario projections vs baseline: KPI trajectories under the hypothetical
- Delta summaries: incremental transactions, value, success-rate movement
- Sensitivity analysis: which assumption drives the outcome most
- Saved, versioned, comparable scenarios

**Features.**
- Guided scenario builder with lever templates: *success-rate improvement, merchant onboarding push, PSP activation campaign, category expansion, failure remediation, adoption incentive*
- Side-by-side comparison of up to N scenarios against baseline
- Assumption transparency: every scenario lists its assumptions and model basis explicitly
- Best/expected/worst-case envelopes on all scenario outputs
- Scenario-to-recommendation linking: promote a validated scenario into an initiative
- Scenario library with ownership, tags, and review status

**User stories.**
- *As a PM, I want to simulate the volume impact of lifting Bank X's success rate from 91% to 94% so that I can size the business case for a remediation program.*
- *As a leadership member, I want best/expected/worst envelopes on any growth scenario so that plans are stress-tested before approval.*
- *As a business team member, I want to compare three merchant-acquisition strategies side by side so that budget goes to the highest-yield option.*

**Business value.** Moves strategic debate from opinion to model; reduces the cost of being wrong by testing before investing; produces defensible business cases with explicit assumptions.

**Future scope.** Multi-lever compound scenarios; Monte Carlo simulation for richer uncertainty envelopes; post-hoc scenario validation (predicted vs realized) feeding model improvement.

---

### 6.7 Executive Report Generation Engine

**Purpose.** Answers *how do we communicate this*. Automates the assembly of executive-grade, narrative-rich reports from live platform intelligence.

**Inputs.**
- KPIs, trends, and decompositions from the Analytics Engine
- Forecasts from the Predictive Engine
- Top recommendations and opportunities of the period
- Report templates (structure, branding, audience level) and schedules
- Narrative generation via the AI Assistant layer

**Outputs.**
- Generated reports: Weekly Business Review, Monthly Ecosystem Report, Quarterly Strategy Review, entity deep-dives (bank/PSP/category), incident retrospectives
- Formats: in-platform interactive report, PDF export, presentation-ready export
- Auto-written executive summaries with key movements, causes, and outlook

**Features.**
- Template library with locked corporate structure and styling
- One-click generation for any period and scope
- Scheduled generation and distribution (e.g., Monday 08:00 weekly review to leadership list)
- AI-drafted narrative sections — every generated statement linked to its source metric
- Human-in-the-loop editing and approval before distribution
- Report archive with version history and immutable published copies
- Section-level refresh (regenerate one section without rebuilding the report)

**User stories.**
- *As a PM, I want my Monday business review generated automatically so that I spend my time on decisions, not slide assembly.*
- *As a leadership member, I want every number in a report traceable to the platform so that board material is audit-proof.*
- *As an operations lead, I want incident retrospective reports pre-populated with the failure analytics so that post-mortems start from facts.*

**Business value.** Eliminates the largest recurring manual cost in the analytics workflow; guarantees consistency between what dashboards show and what executives read; accelerates and standardizes the organization's communication cadence.

**Future scope.** Audience-adaptive narratives (board vs working team from one source); interactive "live" reports that update after publication with change-highlighting; multilingual output.

---

### 6.8 AI Growth Assistant

**Purpose.** The conversational intelligence layer over the entire platform — lets any user ask questions in natural language and receive grounded, sourced, explainable answers.

**Inputs.**
- User natural-language queries and conversation context
- Governed access to Analytics Engine outputs, forecasts, recommendations, opportunities, and Knowledge Hub content — via the platform's service APIs only (never raw database access)
- User role and permissions (answers respect the same access control as the UI)

**Outputs.**
- Natural-language answers with inline charts and metric citations
- Guided drill-down suggestions ("Would you like this split by PSP?")
- Draft artifacts on request: summaries, report sections, talking points
- Deep links into the relevant dashboard/analytics views for every answer

**Features.**
- Natural-language Q&A over all governed KPIs and dimensions ("Why did P2M success rate dip last Tuesday?")
- Grounded generation: every quantitative claim cites the platform metric and query behind it; the assistant refuses rather than guesses when data is unavailable
- Multi-turn analytical conversations with context retention
- Proactive briefings: "three things changed in your product area since yesterday"
- Explain mode: converts any chart or recommendation into plain-language explanation
- Command actions: "generate the weekly report," "add this to my strategy workspace," "simulate a 2% success-rate lift for Bank X"
- Full audit log of assistant interactions and data accessed

**User stories.**
- *As a PM, I want to ask "which PSPs drove last week's volume growth" in plain English so that exploration doesn't require dashboard navigation.*
- *As a leadership member, I want a morning briefing of material changes so that I'm never surprised in a review.*
- *As a new team member, I want to ask the assistant how a metric is defined so that onboarding doesn't depend on tribal knowledge.*

**Business value.** Radically lowers the skill barrier to data — the entire organization gains analyst-level access; increases platform engagement and, through citation discipline, increases trust rather than eroding it.

**Future scope.** Voice interaction; autonomous monitoring agents that investigate anomalies and file draft findings; assistant-initiated opportunity alerts with reasoning chains.

---

### 6.9 Knowledge & Insights Hub

**Purpose.** The institutional memory of the platform — where insights, definitions, research, and learnings are captured, curated, and made discoverable, so intelligence compounds instead of evaporating.

**Inputs.**
- Saved analyses, annotated charts, and pinned insights from all modules
- Published reports and their executive summaries
- Governed KPI dictionary and metric documentation
- User-authored notes, research documents, and decision context
- Recommendation and scenario outcomes

**Outputs.**
- Searchable knowledge base: insights, definitions, reports, research, decisions
- Curated collections ("Autopay growth story," "Bank X reliability history")
- Insight timeline per entity and per metric (everything ever learned about Bank X)
- Retrieval corpus that grounds the AI Assistant's contextual answers

**Features.**
- One-click "save as insight" from any chart or analysis, with auto-captured data context (period, filters, values)
- Tagging, collections, and entity linking (insights attach to banks, PSPs, MCCs, metrics)
- Full-text and semantic search across all knowledge artifacts
- KPI dictionary as a governed, versioned reference section
- Insight lifecycle: draft → published → superseded (stale insights flagged, not silently trusted)
- Subscription feeds: follow an entity or topic, get notified of new insights

**User stories.**
- *As a PM, I want to find every prior analysis of mandate revocation before starting a new one so that I build on existing work instead of repeating it.*
- *As a new joiner, I want the KPI dictionary and curated collections so that I reach productive context in days, not months.*
- *As a leadership member, I want the decision history behind a strategy so that reviews recall why choices were made.*

**Business value.** Converts individual analysis into organizational assets; eliminates repeated work; provides the grounding corpus that makes the AI Assistant institutionally knowledgeable rather than generically fluent.

**Future scope.** Auto-summarization of aging insight clusters; knowledge-graph view linking entities, metrics, insights, and decisions; cross-team insight recommendation ("a payments-ops analysis relevant to your current work exists").

---

### 6.10 Product Strategy Workspace

**Purpose.** Where intelligence becomes managed execution — PMs convert recommendations, opportunities, and scenarios into tracked strategic initiatives with hypotheses, targets, and measured outcomes.

**Inputs.**
- Accepted recommendations and promoted scenarios
- Opportunity cards selected for pursuit
- Initiative metadata from users (owner, hypothesis, target metrics, timeline)
- Live KPI feeds for outcome tracking

**Outputs.**
- Initiative portfolio: status, owner, target vs actual impact
- Hypothesis records: "we believe X action will move Y metric by Z"
- Outcome measurements: automatic before/after KPI tracking per initiative
- Portfolio reviews: aggregate view of strategy execution health

**Features.**
- Initiative builder pre-populated from the source recommendation/opportunity/scenario (full evidence chain attached)
- Explicit hypothesis and success-metric definition required at creation
- Automatic outcome tracking: platform monitors the target metric and reports realized vs predicted impact
- Portfolio board: initiatives by stage, owner, product line, expected value
- Decision log: choices, rationale, and dissent captured at decision points
- Review cadence support: quarterly portfolio review views with outcome scorecards

**User stories.**
- *As a PM, I want every initiative born from a recommendation to carry its evidence with it so that execution never loses its analytical grounding.*
- *As a leadership member, I want a portfolio view of all strategic bets with realized impact so that resource allocation follows results.*
- *As a PM, I want the platform to measure my initiative's actual metric impact so that outcome assessment is objective, not self-reported.*

**Business value.** Closes the full loop — data → insight → recommendation → decision → execution → measured outcome; makes strategy auditable and learning cumulative; the measured-outcome data continuously improves the Recommendation Engine.

**Future scope.** Integration with enterprise project tooling; experiment design support (holdout comparisons where feasible); AI-drafted initiative retrospectives.

---

### 6.11 Explainability & Trust Engine

**Purpose.** The credibility layer. Guarantees that every number, forecast, and recommendation on the platform can be interrogated, traced, and trusted — the difference between a tool PMs consult and a tool executives bet on.

**Inputs.**
- Metric lineage metadata (source tables, transformation logic, KPI definitions)
- Model metadata from the Predictive Engine (features, training window, backtest accuracy)
- Recommendation evidence chains from the Recommendation Engine
- Data pipeline freshness and quality signals

**Outputs.**
- "Why this number" panels: definition, source, computation path, freshness for any KPI
- "Why this forecast" panels: model, drivers, accuracy history, confidence basis
- "Why this recommendation" panels: full evidence chain from raw signal to proposed action
- Data quality and freshness indicators embedded across all modules
- Audit trails: who saw what, when, and on which data version

**Features.**
- Universal "Explain" affordance on every metric, chart, forecast, and recommendation
- Metric lineage browser: KPI → aggregate → source fields
- Model cards for every deployed model: purpose, data, performance, limitations, refresh cadence
- Confidence vocabulary standardized platform-wide (same bands mean the same thing everywhere)
- Data freshness banner: every view declares its as-of timestamp
- Discrepancy reporting: users flag suspect numbers; triage workflow tracks resolution

**User stories.**
- *As a leadership member, I want to click any board-deck number and see its lineage so that I can defend it under scrutiny.*
- *As a PM, I want model accuracy history beside every forecast so that I calibrate my reliance appropriately.*
- *As an operations analyst, I want data-freshness indicators so that I never diagnose an "anomaly" that is actually a late pipeline.*

**Business value.** Trust is the adoption bottleneck for every analytics platform; this module is the structural answer. It also satisfies the audit and governance expectations inherent to NPCI's institutional context.

**Future scope.** Counterfactual explanations for forecasts ("volume would be X had the festival effect not occurred"); automated reconciliation against upstream reference totals; explainability APIs for downstream consumers.

---

### 6.12 Enterprise Administration

**Purpose.** The governance and operations backbone: identity, access, configuration, data operations, and platform health.

**Inputs.**
- User directory and role assignments
- Access policies (module-level and data-scope-level)
- Pipeline schedules, job statuses, data-quality rule results
- Platform telemetry (usage, performance, errors)

**Outputs.**
- User and role administration console
- Access audit logs and compliance reports
- Pipeline monitoring: ingestion status, aggregate refresh status, model retraining status
- Platform configuration: thresholds, business rules, report schedules, alert routing
- Usage analytics: adoption by module, team, and feature

**Features.**
- Role-based access control: Admin, Product Manager, Business User, Leadership (read-optimized), Operations Analyst
- Data-scope permissions where required (e.g., a team restricted to its product line)
- Full audit logging: authentication, data access, exports, admin actions
- Data pipeline console: run history, failures, retry controls, data-quality rule outcomes
- Business-rule administration: recommendation thresholds, alert sensitivities, strategic weights
- Environment and release visibility: current data version, model versions, platform version

**User stories.**
- *As an admin, I want role-based provisioning so that access matches responsibility from day one.*
- *As a compliance stakeholder, I want complete audit trails of data access and exports so that governance reviews are evidence-based.*
- *As an operations analyst, I want pipeline and model-refresh visibility so that I can guarantee the data behind every executive view.*

**Business value.** Makes the platform enterprise-deployable: secure, governable, auditable, and operable — the non-negotiable substrate for everything else.

**Future scope.** SSO/enterprise identity integration; automated access reviews and recertification; self-service data-quality rule authoring; cost/usage chargeback reporting.

---

## 8. Complete User Journey

A representative end-to-end journey for the primary persona (NPCI Product Manager):

### Stage 1 — Login
1. User authenticates (username/password at v1; SSO in future scope).
2. Role-based landing: PM lands on their configured Executive Dashboard; Leadership lands on the executive view.
3. Session context loads: pinned KPIs, followed entities, pending notifications.

### Stage 2 — Dashboard (Situational Awareness)
4. Ecosystem health score and KPI cards render with period deltas — *what happened*.
5. The attention feed shows ranked items: e.g., "P2M success rate down 0.6% WoW — driven by Bank X timeouts."
6. User clicks "Explain" → Explainability panel shows the decomposition evidence and data freshness.

### Stage 3 — Analytics (Investigation)
7. User drills into the Analytics Engine from the alert: failure heatmap by bank × error code confirms concentration.
8. Slice-and-dice: the issue is isolated to one bank, one error class, evenings only — *why it happened*.
9. User saves the analysis as an Insight (auto-captured context) into the Knowledge Hub.

### Stage 4 — Prediction & Recommendation (Decision Support)
10. Predictive panel shows the projected success-rate trajectory if untreated — *what will happen*.
11. The Recommendation Engine has already queued: "Initiate reliability remediation with Bank X — estimated recovery of N lakh transactions/month," with full evidence chain — *what should we do*.
12. User opens the Scenario Simulation Engine: models remediation at two intervention speeds; compares outcome envelopes — *what if*.

### Stage 5 — Strategy (Action)
13. User accepts the recommendation and promotes it, with the winning scenario attached, into the Product Strategy Workspace as an initiative with hypothesis and target metric.
14. Outcome tracking activates automatically: the platform will measure realized impact against the prediction.

### Stage 6 — AI Assistant (Acceleration Throughout)
15. At any point, the user asks the AI Growth Assistant: "Summarize the Bank X issue and our planned response for my leadership sync" — receives a cited, editable summary.
16. Assistant offers a proactive follow-up the next morning: "Bank X error rate improved 0.2% overnight; trajectory updated."

### Stage 7 — Reports (Communication)
17. User triggers report generation: the Weekly Business Review auto-includes the incident, root cause, forecast, and initiated action — *how we communicate*.
18. User reviews the AI-drafted narrative, edits one paragraph, approves.

### Stage 8 — Exports & Distribution
19. Report is exported to PDF/presentation format and distributed to the scheduled leadership list.
20. The published report is archived immutably; every figure remains click-through traceable in the platform copy.

**Journey principle:** the seven canonical questions are answered in a single continuous workflow, without leaving the platform, without writing a query, and without assembling a slide manually.

---

## 9. Complete Feature List & Prioritization

### 9.1 Must Have (V1 — Core Platform)

| # | Feature | Module |
|---|---------|--------|
| M1 | Authentication and role-based access control | Administration |
| M2 | Executive dashboard with core KPI cards, trends, and deltas | Dashboard |
| M3 | Governed KPI dictionary with single-definition metrics | Analytics |
| M4 | Multidimensional KPI explorer (time, bank, PSP, MCC, txn type, error code) | Analytics |
| M5 | Failure analytics suite (error Pareto, bank × PSP heatmap) | Analytics |
| M6 | Period-over-period comparisons with growth rates | Analytics |
| M7 | Core KPI forecasting (volume, value, success rate) with confidence bands | Predictive |
| M8 | Anomaly detection feeding the dashboard attention feed | Predictive |
| M9 | Rule-and-model-based recommendations with impact ranking | Recommendation |
| M10 | Recommendation lifecycle (accept/reject with feedback) | Recommendation |
| M11 | Peer-benchmark gap detection and whitespace views | Opportunity |
| M12 | Report templates + one-click weekly/monthly report generation | Reports |
| M13 | PDF export of reports and analyses | Reports |
| M14 | AI Assistant: grounded natural-language Q&A over governed KPIs | AI Assistant |
| M15 | Universal "Explain this" panels (metric lineage, freshness) | Explainability |
| M16 | Insight saving with auto-captured context; knowledge search | Knowledge Hub |
| M17 | Audit logging (access, exports, admin actions) | Administration |
| M18 | Data pipeline monitoring console | Administration |

### 9.2 Should Have (V1.x — Fast Follow)

| # | Feature | Module |
|---|---------|--------|
| S1 | Scenario Simulation Engine with lever templates and comparisons | Simulation |
| S2 | Product Strategy Workspace with initiative and outcome tracking | Strategy |
| S3 | Scheduled report generation and distribution lists | Reports |
| S4 | Segment-level forecasting (per bank / PSP / MCC) | Predictive |
| S5 | Cohort and funnel analytics (merchant activation, mandate lifecycle) | Analytics |
| S6 | AI Assistant proactive briefings and command actions | AI Assistant |
| S7 | Watchlists and subscription notifications | Opportunity / Hub |
| S8 | Model cards and forecast-accuracy history views | Explainability |
| S9 | Configurable dashboard layouts per role | Dashboard |
| S10 | Playbook templates for recurring recommendations | Recommendation |
| S11 | Discrepancy flagging and triage workflow | Explainability |
| S12 | Presentation-format report export | Reports |

### 9.3 Future (V2+)

| # | Feature | Module |
|---|---------|--------|
| F1 | Real-time/streaming dashboard tiles | Dashboard |
| F2 | Monte Carlo and multi-lever compound scenarios | Simulation |
| F3 | Autonomous AI monitoring agents with draft findings | AI Assistant |
| F4 | Voice interaction and mobile executive app | AI Assistant / Dashboard |
| F5 | SSO / enterprise identity integration and access recertification | Administration |
| F6 | Knowledge graph of entities, metrics, insights, and decisions | Knowledge Hub |
| F7 | Outcome-tuned recommendation ranking (learning from realized impact) | Recommendation |
| F8 | External signal enrichment for forecasting | Predictive |
| F9 | Audience-adaptive and multilingual report narratives | Reports |
| F10 | Experiment design support with holdout measurement | Strategy |

---

## 10. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | The system shall authenticate users and enforce role-based authorization on every API endpoint and UI module. |
| FR-02 | The system shall compute all KPIs from governed, versioned definitions; no module shall maintain an independent metric implementation. |
| FR-03 | The system shall support KPI exploration across the dimensions defined in Database Architecture v1.0 (time, transaction type, payer/payee bank, PSP, merchant category, initiation mode, response/error code, mandate attributes). |
| FR-04 | The system shall present period-over-period deltas (DoD, WoW, MoM, QoQ, YoY) with statistical significance indication. |
| FR-05 | The system shall generate forecasts for core KPIs at 7/30/90-day horizons with prediction intervals, and display forecast accuracy history. |
| FR-06 | The system shall detect anomalies in KPI series and surface them, ranked by estimated business impact, in the dashboard attention feed. |
| FR-07 | The system shall produce recommendations containing: action, target entity, rationale, estimated impact, confidence, and a complete evidence chain. |
| FR-08 | The system shall track recommendation lifecycle states and capture accept/reject feedback with reasons. |
| FR-09 | The system shall identify opportunity candidates via peer benchmarking and whitespace analysis, each with a size estimate and supporting evidence. |
| FR-10 | The system shall allow users to define, run, save, and compare scenarios against baseline forecasts, with explicit assumption listings. |
| FR-11 | The system shall generate reports from templates for defined periods and scopes, including AI-drafted narrative sections with metric citations, subject to human approval before distribution. |
| FR-12 | The system shall export reports and analyses to PDF (V1) and presentation formats (V1.x). |
| FR-13 | The AI Assistant shall answer natural-language questions using only governed platform data accessed through service APIs, shall cite sources for quantitative claims, and shall decline to answer when data is unavailable. |
| FR-14 | The system shall provide an "Explain" capability on every metric, forecast, and recommendation, exposing definition, lineage, freshness, and (for models) accuracy metadata. |
| FR-15 | The system shall allow saving any analysis as an insight with automatically captured context (filters, period, values), and shall make all knowledge artifacts searchable. |
| FR-16 | The system shall support initiative creation from recommendations/scenarios/opportunities, with hypothesis, target metric, and automatic outcome measurement. |
| FR-17 | The system shall display data freshness (as-of timestamp) on every analytical view. |
| FR-18 | The system shall log all authentication events, data exports, admin actions, and AI Assistant data access to an immutable audit trail. |
| FR-19 | The system shall provide administrators with pipeline run status, data-quality rule outcomes, and model refresh status. |
| FR-20 | The system shall support saved analyses, watchlists, and notification subscriptions per user. |

---

## 11. Non-Functional Requirements

### 11.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-P1 | Dashboard initial load: ≤ 2 seconds (P95) using pre-computed aggregates. |
| NFR-P2 | Interactive analytics queries (aggregate-backed): ≤ 3 seconds (P95); deep ad-hoc slices: ≤ 10 seconds (P95). |
| NFR-P3 | AI Assistant first-token response: ≤ 3 seconds; complete grounded answer: ≤ 15 seconds (P95). |
| NFR-P4 | Standard report generation: ≤ 60 seconds end-to-end. |
| NFR-P5 | Batch pipelines (aggregation, scoring) complete within the nightly window with ≥ 25% headroom. |

### 11.2 Scalability

| ID | Requirement |
|----|-------------|
| NFR-S1 | Data tier sized for multi-year transaction history at ecosystem scale per Database Architecture v1.0 partitioning strategy; analytics must not degrade super-linearly with history growth. |
| NFR-S2 | Application tier horizontally scalable (stateless API services behind a load balancer). |
| NFR-S3 | Support 200 concurrent active users at launch; architecture must scale to 1,000+ without redesign. |
| NFR-S4 | ML training and inference workloads isolated from interactive query capacity. |

### 11.3 Security

| ID | Requirement |
|----|-------------|
| NFR-SE1 | Encryption in transit (TLS 1.2+) for all connections; encryption at rest for the data tier. |
| NFR-SE2 | Role-based access control enforced at the API layer; least-privilege defaults. |
| NFR-SE3 | The analytical dataset shall contain no raw customer PII beyond what Database Architecture v1.0 defines; any sensitive identifiers masked or pseudonymized in all UI and export surfaces. |
| NFR-SE4 | Complete, tamper-evident audit logging (see FR-18); logs retained per NPCI policy. |
| NFR-SE5 | AI Assistant operates under the caller's permissions; no privilege escalation via natural language; prompt-injection defenses on any content entering LLM context. |
| NFR-SE6 | Secrets managed via environment/secret-store configuration; never in source control. |

### 11.4 Reliability

| ID | Requirement |
|----|-------------|
| NFR-R1 | No single point of failure in the application tier; database HA per the frozen data-tier deployment design. |
| NFR-R2 | Pipeline failures must be detected, alerted, and re-runnable without manual data surgery; partial-load states must be impossible or clearly flagged. |
| NFR-R3 | Model-serving failure degrades gracefully: platform continues with descriptive/diagnostic capability and clearly marks predictive surfaces as unavailable. |
| NFR-R4 | RPO ≤ 24 hours (batch-analytical system); RTO ≤ 4 hours. |

### 11.5 Availability

| ID | Requirement |
|----|-------------|
| NFR-A1 | 99.5% availability during business hours (07:00–22:00 IST) at V1; path to 99.9%. |
| NFR-A2 | Planned maintenance outside business hours with advance notice. |
| NFR-A3 | Read-heavy design: dashboards remain served from aggregates even during ingestion windows. |

### 11.6 Maintainability

| ID | Requirement |
|----|-------------|
| NFR-M1 | Backend follows the frozen Clean Architecture layering (api → services → repositories → models); new modules must conform. |
| NFR-M2 | All schema changes via Alembic migrations; no manual DDL. |
| NFR-M3 | KPI definitions, business rules, and thresholds configurable without code deployment. |
| NFR-M4 | Automated test coverage for all service-layer business logic; CI gates on test pass. |
| NFR-M5 | Structured logging and metrics instrumentation across all services; every user-facing error traceable to a correlated log entry. |
| NFR-M6 | Versioned APIs; no breaking changes without a deprecation window. |

---

## 12. System Architecture

The system architecture applies the layered product architecture (§5) to the **frozen backend foundation** — a FastAPI application organized by Clean Architecture, with PostgreSQL persistence per Database Architecture v1.0. This section describes composition, not redesign.

```
                        ┌──────────────────────────────┐
                        │        Web Frontend (SPA)    │
                        │  Dashboard · Analytics · AI  │
                        └──────────────┬───────────────┘
                                       │ HTTPS / REST (versioned JSON APIs)
                        ┌──────────────▼───────────────┐
                        │        API Gateway Layer     │
                        │  AuthN/AuthZ · rate limiting │
                        └──────────────┬───────────────┘
              ┌────────────────────────┼────────────────────────┐
              │            FastAPI Application (frozen layering) │
              │  api/ routers → services/ → repositories/ → models/ │
              │                                                  │
              │  Service groups:                                 │
              │   • Analytics services (KPI, slicing, decomposition) │
              │   • Intelligence services (forecast, recommend,      │
              │     discover, simulate)                          │
              │   • Narrative services (reports, AI assistant       │
              │     orchestration)                               │
              │   • Workspace services (insights, initiatives)      │
              │   • Admin services (users, roles, audit, pipelines) │
              └───────┬──────────────────────────┬───────────────┘
                      │                          │
        ┌─────────────▼────────────┐   ┌─────────▼──────────────┐
        │  PostgreSQL (frozen —    │   │  Async Workers / Jobs  │
        │  Database Architecture   │   │  aggregation · model   │
        │  v1.0): facts, masters,  │   │  scoring · report      │
        │  aggregates, app tables  │   │  builds · discovery    │
        └──────────────────────────┘   │  sweeps · schedules    │
                                       └─────────┬──────────────┘
                                       ┌─────────▼──────────────┐
                                       │  ML Runtime & LLM      │
                                       │  Integration Layer     │
                                       │  (model registry,      │
                                       │  inference, guarded    │
                                       │  LLM gateway)          │
                                       └────────────────────────┘
```

**Key architectural decisions:**

| Decision | Rationale |
|---|---|
| Single FastAPI application with modular service groups (modular monolith) at V1 | Matches the frozen foundation; fastest path to value; clean seams allow later extraction of heavy services (ML, reports) if scale demands |
| All computation-heavy work (aggregation, training, scoring, report builds) in asynchronous workers | Keeps interactive APIs fast; isolates batch load per NFR-S4 |
| Interactive reads served from pre-computed aggregate tables | Meets NFR-P1/P2 at ecosystem data volumes |
| LLM access through a guarded gateway service only | Enforces grounding, citation, permission scoping, and audit (NFR-SE5); no module calls an LLM directly |
| Frontend is a pure API client | Enforces the single-source-of-truth rule; enables future mobile/wallboard clients on the same contracts |

---

## 13. Technology Stack

The stack extends the established foundation; frozen choices are marked.

| Layer | Technology | Status |
|---|---|---|
| **Backend framework** | Python 3.11+, FastAPI, Uvicorn (ASGI) | Frozen (foundation) |
| **API contracts** | Pydantic v2 schemas, versioned REST | Frozen (foundation) |
| **ORM / migrations** | SQLAlchemy, Alembic | Frozen (foundation) |
| **Database** | PostgreSQL (psycopg2) per Database Architecture v1.0 | Frozen |
| **Configuration** | pydantic-settings, environment-driven (.env) | Frozen (foundation) |
| **Analytics computation** | Pandas / NumPy within analytics services; SQL-pushdown to aggregates for heavy lifting | Planned |
| **Machine learning** | scikit-learn (baselines, anomaly detection); statsmodels / Prophet-class methods for time series; XGBoost/LightGBM for tabular models | Planned |
| **Model management** | Model registry with versioned artifacts and metadata (model cards) | Planned |
| **Async jobs / scheduling** | Task queue + scheduler (Celery/APScheduler-class) for pipelines, scoring, report builds | Planned |
| **AI Assistant** | LLM via guarded gateway; retrieval over Knowledge Hub + governed KPI APIs (RAG pattern); Claude-class model API | Planned |
| **Report rendering** | HTML template → PDF pipeline; presentation export in V1.x | Planned |
| **Frontend** | Modern SPA framework (React-class) with a component design system and charting library | Planned |
| **AuthN/AuthZ** | JWT-based sessions at V1; RBAC middleware; SSO-ready design | Planned |
| **Observability** | Structured logging, metrics, and tracing instrumentation | Planned |
| **Deployment** | Containerized services; environment parity dev → staging → production | Planned |

---

## 14. Database Overview

> **Governing document: Database Architecture v1.0 (Frozen).** This specification references that design and does not modify it. Any change requires a formal revision of that document — not of this one.

**Summary of the frozen design as consumed by this platform:**

- **Transaction fact store** — the canonical UPI transaction dataset, including: transaction identity and type (P2P, merchant payment, mandate operations), timestamps, payer/payee addresses, banks, PSPs and their organization IDs, merchant attributes (MCC, genre, onboarding type, verified name), amounts, purpose and initiation mode, credential types, response codes, error codes, and status descriptions. This is the ground truth every module ultimately traces back to.
- **Master / dimension data** — banks, PSPs/organizations, merchants, categories (MCC), geography, and calendar dimensions supporting the dimensional slicing in §6.2.
- **Aggregate tables** — pre-computed rollups (by day × dimension combinations) that serve all interactive dashboard and analytics reads, per the performance strategy in §11.1.
- **Application tables** — platform-owned entities (users, roles, insights, recommendations, initiatives, reports, audit events) as defined in the frozen architecture's application schema section.
- **Migration discipline** — all schema evolution via Alembic under the frozen governance rules.

**Rules for all modules:**

1. No module queries transaction facts directly for interactive use; interactive paths use aggregates.
2. No module defines private copies of dimensional attributes; master data is joined, not duplicated.
3. The Analytics Engine is the only layer that computes KPIs from stored data; all other modules consume its outputs.

---

## 15. Analytics Architecture

The Analytics Engine is structured as four internal stages:

```
 Source Data (frozen schema)
      │
      ▼
 1. AGGREGATION PIPELINE  (scheduled, async workers)
    • Validates and loads new transaction data windows
    • Builds/refreshes aggregate tables: daily × {txn type, bank, PSP,
      MCC, initiation mode, response/error code, geography} rollups
    • Runs data-quality rules; publishes freshness metadata
      │
      ▼
 2. METRIC LAYER  (governed KPI dictionary)
    • Single, versioned definition per KPI (volume, value, success rate,
      failure rate, active entities, ticket size, mix ratios, mandate
      funnel metrics)
    • Definitions resolve to aggregate-backed query plans
      │
      ▼
 3. ANALYTICAL SERVICES  (interactive, API layer)
    • Slicing/pivot service: any KPI × any dimension set
    • Comparison service: period vs period, entity vs entity, significance
    • Decomposition service: contribution analysis for metric movements
    • Cohort & funnel service: activation cohorts, mandate lifecycles
      │
      ▼
 4. STATISTICAL SERVICES  (shared with Intelligence Layer)
    • Trend/seasonality decomposition, changepoint detection
    • Significance testing, benchmark scoring (peer-group statistics)
```

**Design commitments:**

- **One metric, one definition** — the KPI dictionary is code-reviewed and versioned; UI, reports, AI Assistant, and recommendations all resolve through it.
- **Aggregates as the interactive substrate** — fact-level queries are reserved for pipeline and deep-forensic paths.
- **Decomposition as a first-class service** — "why did this metric move" is an API, not an analyst exercise; it powers the Explainability Engine and the Recommendation evidence chains.
- **Freshness metadata everywhere** — every analytical response carries its as-of timestamp, consumed by the Trust Engine's freshness banners.

---

## 16. Machine Learning Architecture

```
 Analytics Layer (KPI series, aggregates)
      │
      ▼
 FEATURE PREPARATION
   • Time-series feature frames per KPI × segment
   • Calendar/festival features, lag and rolling-window features
   • Entity features (bank tier, PSP scale, MCC group)
      │
      ▼
 MODEL FAMILIES
   1. Forecasting     — per-KPI, per-segment time-series models
                        (statistical baselines → gradient-boosted /
                        Prophet-class challengers)
   2. Anomaly         — residual-based and statistical-process detection
      Detection         on KPI series; severity scoring by impact
   3. Benchmarking    — peer-group expectation models for gap detection
                        (Opportunity Discovery)
   4. Relationship /  — elasticity estimation linking levers to outcomes
      Elasticity        (Scenario Simulation substrate)
      │
      ▼
 MODEL LIFECYCLE
   • Registry: versioned artifacts + model cards (purpose, data window,
     features, backtest metrics, limitations)
   • Scheduled retraining with champion/challenger evaluation
   • Automatic backtesting; accuracy history persisted for the
     Explainability Engine
   • Guardrails: models failing quality gates never auto-promote
      │
      ▼
 SERVING
   • Batch scoring (nightly): forecasts, anomaly scores, benchmark gaps
     written to application tables for instant read
   • On-demand inference: scenario simulation requests only
   • Graceful degradation per NFR-R3
```

**Principles:**

- **Boring first, clever later.** Statistical baselines ship first and set the accuracy bar; complex models must beat them in backtests to be promoted.
- **Batch-scored by default.** Predictions are precomputed and stored, keeping the interactive experience fast and the serving surface simple.
- **Every model is documented.** No model serves users without a model card visible in the Explainability Engine.
- **Uncertainty is part of the output.** No point forecasts without intervals, anywhere in the platform.

---

## 17. Recommendation Architecture

```
 SIGNAL SOURCES
   • Analytics decompositions (root-caused problems)
   • Predictive early warnings (forecasted threshold breaches)
   • Opportunity Discovery outputs (gaps, whitespace, momentum, at-risk)
      │
      ▼
 1. CANDIDATE GENERATION
   • Rule library: admin-configured business rules map signal patterns
     to action templates (e.g., success-rate breach → remediation playbook)
   • Playbook templates define action structure per recommendation type
      │
      ▼
 2. IMPACT ESTIMATION
   • Sizing via benchmark-closure and elasticity models
     ("if gap closes to peer median → +N txns/month")
   • Confidence scoring from signal strength and model accuracy
      │
      ▼
 3. RANKING & DEDUPLICATION
   • Score = estimated impact × confidence × strategic weight
     (strategic weights admin-configured per planning cycle)
   • Conflict/duplicate detection across candidates and existing initiatives
      │
      ▼
 4. PRESENTATION & LIFECYCLE
   • Recommendation cards with full evidence chain (Explainability)
   • Lifecycle: proposed → review → accepted/rejected (+reason) →
     in execution (Strategy Workspace) → outcome measured → closed
      │
      ▼
 5. FEEDBACK LOOP
   • Accept/reject reasons and measured outcomes persisted
   • Periodic recalibration of impact models and ranking weights
```

**Principles:** every recommendation is *explainable* (full evidence chain), *sized* (business-unit impact), *actionable* (concrete next step, not "investigate further"), and *accountable* (its predicted impact is later compared to measured reality).

---

## 18. Report Generation Architecture

```
 TRIGGERS
   • On-demand (user)  • Scheduled (cron-style)  • Event-driven (V2: incident)
      │
      ▼
 1. TEMPLATE RESOLUTION
   • Template registry: Weekly Review, Monthly Ecosystem, Quarterly
     Strategy, Entity Deep-Dive, Incident Retrospective
   • Templates define sections, required metrics, chart specs, branding
      │
      ▼
 2. DATA ASSEMBLY  (async worker)
   • Pulls all section data from Analytics/Predictive/Recommendation
     service APIs for the report period and scope
   • Snapshot semantics: report data is frozen at generation time with
     recorded as-of timestamps
      │
      ▼
 3. NARRATIVE GENERATION
   • AI Assistant layer drafts section narratives from assembled data only
   • Every generated sentence with a quantitative claim carries a metric
     citation; uncited claims are rejected by the pipeline
      │
      ▼
 4. HUMAN REVIEW & APPROVAL
   • Owner edits/approves in-platform; section-level regeneration
   • Approval required before any distribution (FR-11)
      │
      ▼
 5. RENDERING & DISTRIBUTION
   • Interactive in-platform report (click-through to live views)
   • PDF export (V1); presentation export (V1.x)
   • Distribution to configured lists; publication archived immutably
     with version history and audit record
```

---

## 19. AI Assistant Architecture

```
 USER QUERY (natural language, multi-turn)
      │
      ▼
 1. GUARDED GATEWAY  (single LLM entry point, platform-wide)
   • AuthN context attached: assistant acts strictly as the caller
   • Input screening (prompt-injection defenses, scope filtering)
   • Full audit logging of query, tools invoked, data accessed
      │
      ▼
 2. INTENT & PLANNING
   • Classify: data question / explanation / command action / drafting
   • Plan tool calls against governed platform APIs
      │
      ▼
 3. GROUNDED RETRIEVAL & TOOL USE
   • KPI queries → Analytics service APIs (never SQL, never raw tables)
   • Forecasts/recommendations/opportunities → Intelligence service APIs
   • Definitions, prior insights, reports → Knowledge Hub retrieval (RAG)
   • Command actions (generate report, save insight, create scenario) →
     Workspace APIs with user confirmation for state-changing actions
      │
      ▼
 4. RESPONSE SYNTHESIS
   • Answer composed ONLY from retrieved platform data
   • Every quantitative claim cites metric + period + as-of timestamp
   • "I don't have data for that" is a mandated response when retrieval
     is empty — the assistant never estimates ecosystem numbers
      │
      ▼
 5. PRESENTATION
   • Answer + inline charts + deep links to source views
   • Suggested drill-downs; conversation context retained
```

**Trust contract (non-negotiable):** the assistant is a *reader and narrator of governed data*, not an oracle. Permissions mirror the UI; every answer is auditable; groundedness is enforced structurally (citation-or-refuse), not by prompt hope.

---

## 20. Implementation Roadmap

Phased to deliver visible value early while respecting dependencies. Each phase produces a demonstrable increment.

### Phase 1 — Backend Foundation *(complete — frozen)*
- FastAPI application skeleton with Clean Architecture layering
- Configuration management, environment handling, health endpoints
- Repository structure, dependency baseline

### Phase 2 — Database & Data Layer
- Implement Database Architecture v1.0: fact, master, aggregate, and application tables via Alembic migrations
- Ingestion pipeline for the transaction dataset with validation and data-quality rules
- Aggregate build pipeline and freshness metadata publication

### Phase 3 — Analytics Engine
- Governed KPI dictionary and metric layer
- Slicing/pivot, comparison, and decomposition services + APIs
- Failure analytics and mandate funnel services
- Statistical services (trend, seasonality, significance, benchmarks)

### Phase 4 — Machine Learning
- Feature preparation pipelines from KPI series
- Forecasting models (core KPIs) with backtesting and registry
- Anomaly detection and severity scoring
- Nightly batch scoring into application tables; model cards

### Phase 5 — Recommendations & Opportunity Discovery
- Rule library and playbook templates; candidate generation
- Impact estimation and ranking; recommendation lifecycle APIs
- Peer benchmarking and whitespace analysis; opportunity cards
- Evidence-chain assembly (Explainability integration)

### Phase 6 — Reports
- Template registry (Weekly, Monthly, Deep-Dive)
- Data assembly workers with snapshot semantics
- PDF rendering pipeline; archive and versioning
- Scheduling and distribution (V1.x)

### Phase 7 — AI Growth Assistant
- Guarded LLM gateway with audit and permission scoping
- Tool integration over Analytics/Intelligence/Knowledge APIs
- Grounded Q&A with citation enforcement
- Narrative generation service for the Report engine (shared layer)

### Phase 8 — Frontend
- Design system, application shell, authentication flows
- Executive Dashboard → Analytics Workbench → Recommendations/Opportunities → Reports → AI Assistant chat → Knowledge Hub → Strategy Workspace → Admin console
- Explainability panels and freshness indicators woven through all views

### Phase 9 — Deployment & Hardening
- Containerization; dev/staging/production parity
- Observability stack (logging, metrics, tracing, alerting)
- Security hardening, audit verification, performance/load testing against NFRs
- Pilot rollout → feedback iteration → general internal availability

**Dependency rule:** Phases 3→7 each consume only the outputs of earlier phases; frontend (Phase 8) develops in parallel against stabilized API contracts from Phase 3 onward.

---

## 21. Success Metrics

### 21.1 Adoption

| Metric | Target (6 months post-launch) |
|---|---|
| Weekly active users among target PM population | ≥ 80% |
| Leadership monthly active usage | ≥ 90% of executive cohort |
| AI Assistant queries per active user per week | ≥ 10 |
| Insights saved to Knowledge Hub per month | Sustained growth quarter-over-quarter |

### 21.2 Efficiency

| Metric | Target |
|---|---|
| Median time from PM question to grounded answer | < 5 minutes (baseline: days) |
| Executive report assembly time | < 1 hour including review (baseline: days) |
| Analyst hours on recurring reporting | −70% |

### 21.3 Intelligence Quality

| Metric | Target |
|---|---|
| Core KPI 30-day forecast accuracy (MAPE) | ≤ 10%, improving quarterly |
| Anomaly precision (alerts judged actionable) | ≥ 70% |
| Recommendation acceptance rate | ≥ 40% |
| Accepted recommendations with realized impact ≥ 50% of estimate | ≥ 60% |

### 21.4 Trust & Governance

| Metric | Target |
|---|---|
| KPIs with complete lineage/explainability coverage | 100% |
| AI Assistant answers with full citations | 100% (structural) |
| Data-freshness SLA adherence (aggregates current by 08:00 IST) | ≥ 99% |
| Reported metric discrepancies resolved within SLA | ≥ 95% |

### 21.5 Business Outcomes (Ultimate Test)

| Metric | Signal |
|---|---|
| Strategic initiatives originating from platform recommendations/opportunities | Growing share of the initiative portfolio |
| Measured KPI impact attributable to platform-driven initiatives | Positive, documented in Strategy Workspace outcome records |
| Executive reviews conducted directly from platform artifacts | Platform is the default medium of business review |

---

## 22. Future Vision

**Horizon 1 — Intelligence Deepening (12–18 months).** Segment-level forecasting everywhere; outcome-tuned recommendation ranking; compound and Monte Carlo scenarios; knowledge graph connecting entities, metrics, insights, and decisions; SSO and enterprise identity integration.

**Horizon 2 — Autonomous Intelligence (18–30 months).** Monitoring agents that detect, investigate, and draft findings on anomalies before any human asks; recommendations that arrive with pre-run simulations attached; report generation that is fully event-driven; the assistant as a proactive analytical colleague with an audit trail.

**Horizon 3 — Ecosystem Intelligence Fabric (30+ months).** The platform pattern extends beyond UPI to NPCI's broader product portfolio as a shared intelligence fabric — common metric governance, shared explainability standards, portfolio-level opportunity discovery, and cross-product scenario planning. Selected, governed intelligence surfaces may be extended to ecosystem partners (banks, PSPs) as scorecard services, turning internal intelligence into ecosystem-wide performance improvement.

**The enduring thesis:** the value of the UPI ecosystem's data is bounded not by its volume but by the speed and confidence with which it becomes decisions. This platform exists to remove that bound.

---

*— End of Product Design Specification v1.0 —*

*This document is the single source of truth for product scope and design. Changes require a versioned revision. The Database Architecture v1.0 and backend foundation remain governed by their own frozen documents.*
