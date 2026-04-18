# Product Decision Record: Why Multi-Agent Architecture

> Key product decisions behind the system's architecture, model selection, and agent collaboration patterns.

---

## Decision 1: Multi-Agent vs. Single Agent

### Problem

The quality inspection workflow has 5 stages: data collection → scoring → report generation → rectification review → cross-project analysis. Should one agent handle all, or should we split?

### Decision

**Split into 5 specialized agents, each with a single responsibility.**

### Rationale

**1. Prompt interference.** A single agent handling scoring + reporting + review simultaneously needs a bloated system prompt: "You are a scoring expert AND a report writer AND a review auditor." LLM attention gets diluted across domains. In testing, single-agent accuracy drops ~15-20% on multi-domain tasks.

**2. Context window constraints.** Cross-project analysis needs to load multiple scoring matrices, issue lists, and trend data simultaneously. If the same agent also carries scoring logic and report templates, token consumption multiplies and signal gets buried in noise.

**3. Fault isolation.** If the scoring agent has a bug, the report agent still works. The rectification agent is unaffected. In a monolithic agent, one failure cascades everywhere.

**4. Independent iteration.** Want to improve scoring logic? Change Agent 2 only, deploy, done. No impact on other agents. Like microservices vs. monolith — but for AI.

### Supporting Evidence

Anthropic's 2026 "Building Effective AI Agents" reports that for complex tasks requiring multiple independent directions, multi-agent systems outperform single-agent by 90%+. Our scenario fits this exactly — scoring, reporting, and reviewing are three fundamentally different cognitive tasks.

---

## Decision 2: Agent Communication via Database

### Problem

After Agent 2 finishes scoring, how does Agent 3 get the scoring data? Direct function call, or through a shared data layer?

### Decision

**Database as the communication bus. No direct agent-to-agent calls.**

### Rationale

**1. Sequential dependency ≠ runtime coupling.** Yes, the business flow is linear (score first, then report). But agents don't need to call each other at runtime. Agent 2 writes to `scoring_results` table; Agent 3 reads from it independently — classic producer-consumer pattern.

**2. Resilience.** If Agent A calls Agent B directly and B times out, A fails too. With database decoupling, downstream agents can retry anytime, independent of upstream state. This was validated in production: during a scoring agent outage, report generation continued normally using existing scoring data.

**3. Audit trail.** Every step is recorded in the database. If a report has issues, trace back: report content → scoring results → inspection records → raw data. With direct calls, intermediate state lives in memory — impossible to debug.

**4. Reusability.** The analysis agent also needs scoring data. With DB sharing, multiple consumers read the same data — zero recomputation. Direct calls would require re-running scoring just for analysis.

---

## Decision 3: Cost-Aware Model Selection

### Problem

The system calls LLMs for 4 different tasks. Should we use the same model everywhere?

### Decision

**Match model to task characteristics. Don't use a sledgehammer to hang a picture.**

| Agent | Model | Why |
|---|---|---|
| Agent 1 (Data Collection) | No LLM | Form input + photo capture only. Zero AI cost. |
| Agent 2 (Scoring) | Qwen-Plus | Structured task: each standard → one score. Faster, cheaper. |
| Agent 3 (Report Gen) | DeepSeek | Long-form professional report with analysis. Needs stronger reasoning. |
| Agent 4 (Rectification) | Qwen-VL + Qwen-Plus | Needs vision (inspect photos) and judgment. Qwen-VL handles multimodal. |
| Agent 5 (Analysis) | DeepSeek | Cross-project comparison needs deep synthesis across reports. |

### Principle

High-frequency + structured → lighter model (Qwen). Low-frequency + complex reasoning → stronger model (DeepSeek). This keeps operational costs proportional to task value.

---

## Decision 4: LangGraph over Raw LLM API Calls

### Problem

Agents need multi-step execution (e.g., scoring agent calls LLM 8 times for 8 modules). Use LangGraph for orchestration, or just write a for-loop calling the API?

### Decision

**Use LangGraph framework for agent orchestration.**

### Rationale

1. **Structured state management.** LangGraph's TypedDict State provides reliable cross-step state passing, better than maintaining manual state dicts.
2. **Node-level observability.** Each agent node has independent execution logs — critical for debugging "why did the scoring agent score module 4 incorrectly at 14:22".
3. **Progress tracking.** Agent progress (current_step, progress_pct) is natively exposed via LangGraph state — the frontend shows real-time progress bars to users.

---

## Decision 5: No Agent-to-Agent "Conversation"

### Problem

Some agent frameworks (AutoGen, CrewAI) emphasize agents "talking" to each other — A tells B what to do. Why doesn't this system use that pattern?

### Decision

**Explicit input-output contracts. No agent dialogue.**

### Rationale

Quality inspection is a deterministic business process, not open-ended research. The scoring → reporting → review pipeline is fixed. Introducing agent "discussion" only adds uncertainty and reduces reliability.

Anthropic's architecture guidance confirms: for predictable business workflows, sequential workflows outperform collaborative/chat patterns. Our scenario matches this exactly.

---

## What I'd Do Differently

1. **Centralized prompt management.** Currently prompts are scattered across state.py / nodes.py files. Would add a Prompt Manager with versioning and A/B testing support.

2. **Automated output quality evaluation.** Scoring agent results are spot-checked manually. Would add an Evaluator-Optimizer pattern to auto-assess scoring quality.

3. **LLM response caching.** Re-triggering scoring for the same inspection data re-calls the LLM. A cache layer would save cost on re-runs.

4. **Batch processing for rectification review.** Currently reviews items one by one. For 50+ rectification items, batch API calls would be faster.

---

## References

- [Building Effective AI Agents — Anthropic (2026)](https://www.anthropic.com/engineering/building-effective-agents)
- [README.md](README.md) | [PRD.md](PRD.md) | [AGENTS.md](AGENTS.md) | [TECH_DESIGN.md](TECH_DESIGN.md)
