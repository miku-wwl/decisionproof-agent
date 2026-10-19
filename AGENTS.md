# AGENTS.md — DecisionProof Agent (Open Agent Hackathon 2026)

## Purpose

This repository is a **Hackathon application that consumes an existing Python Agent Runtime**. Build the competition-specific product, **not another agent execution framework**.

**Shared runtime:** [Agentic Intent Gate](https://github.com/miku-wwl/agentic-intent-gate)<br>
**Python distribution:** `agentic-intent-gate`<br>
**Public integration module:** `agentic_intent_gate.runtime`<br>
**Qualified release:** `v0.2.0` (verified annotated Git tag; Python 3.13; MIT)<br>
**Pinned release commit:** `7261fdd2f47d2b15fabe8faac527eeee37338eb1`

The annotated tag `v0.2.0` peels to the pinned commit above. This is a **Git release, not a PyPI publication**. Use the immutable full commit SHA, **not** a moving `main` branch. When upgrading in the future, verify the tag, peeled commit, installed version, and lockfile. Never embed private Git credentials or external-service secrets in URLs, code, screenshots, or logs.

**Repository scope:** These are the root instructions for `decisionproof-agent`, the independent **Kiwi** team entry in the **Open Agent Hackathon 2026**. Do not copy the core repository's developer-only `AGENTS.md` into this consumer project. If local nested instructions exist, read and reconcile them; do not weaken these core safety constraints.

## Competition Identity, Goal, and Source of Truth

- **Application:** DecisionProof Agent (working name); repository `decisionproof-agent`; team **Kiwi** (solo entry).
- **Event:** [Open Agent Hackathon 2026](https://academy.genai.works/courses/open-agent-hackathon-2026/details) / [HackOS event](https://hackathon.genai.works/).
- **Provisional target:** Track 3 — Reasoning Architecture. Confirm exact track definition, eligibility, pre-existing-code policy, and any later rule changes in the authenticated event resources **before** locking submission decisions.
- **Product objective:** Solve **one narrowly defined real problem** using traceable source evidence, meaningful Nemotron reasoning, genuinely integrated Zetaris context, a bounded AIG-controlled side effect, and a judge-friendly UI that shows why the decision was made and what happened.
- **Not the objective:** A generic chat interface, a new Agent Runtime, a broad autonomous orchestration platform, a collection of unconnected features, or a security-only demo with no user value.
- **Rules hierarchy:** Follow applicable laws, security and authorization requirements, the **current official organizer rules**, and then this repository's implementation guidance. When requirements conflict, stop and document the conflict; do not silently choose a convenient interpretation.
- **Unconfirmed statements:** Record as `UNVERIFIED`, with the source, the missing fact, and a concrete verification action. Official public descriptions are useful, but authenticated HackOS rules and organizer clarifications may add constraints.

### Official competition technology requirements

The public event course states that **every submission integrates Zetaris**, **teams use Cursor for development**, and the product **runs on NVIDIA Nemotron**, directly or through Meterless. Treat all three as mandatory unless an authoritative organizer rule supersedes them.

- **Zetaris (Data):** Use it in the working application's actual retrieval/data-context path. A static screenshot, disconnected test, or fabricated response is not sponsor integration.
- **NVIDIA Nemotron (Power):** Use genuine inference for a material part of the agent's reasoning/decision path; Meterless is an allowed access path, not a substitute for proving which model actually ran. Do not silently swap to another model or mislabel model outputs.
- **Cursor (Build):** Carry out **substantive development in Cursor** and maintain truthful evidence of its use. Claude Code or Codex may assist, but opening Cursor without doing real work there does not satisfy the intent of the requirement.
- **Evidence:** Record exact API/SDK versions, model identifier and provider path, relevant configuration (redacted), safe trace/run IDs, reproducible smoke tests, and timestamps. Never invent sponsor credits, access, successful connectivity, or approval.

### Official build-window boundary (UTC)

- **Build opens:** `2026-10-22T00:00:00Z` (**2026-10-22 13:00 NZDT**).
- **Submissions close:** `2026-10-27T23:45:00Z` (**2026-10-28 12:45 NZDT**).
- **Before kickoff:** This repository may contain `AGENTS.md`, design notes, dependency pinning, account/environment checks, standalone sponsor connection tests, and planning **subject to event rules**. Do **not** implement competition-specific production features before the build window unless the official rules explicitly permit it. Do not assert that pre-event code is eligible to be judged.
- **During build:** Implement and test new product features with traceable dated commits/change evidence. Disclose the pre-existing AIG dependency separately from in-window competition-specific work.
- **After deadline:** Do not imply late changes were part of the judged submission. Preserve an identifiable submission commit and submitted evidence.

### Submission and judging checklist

The public event describes a **1–4 minute demo video, slide deck, GitHub repository with README, and a clear sponsor-technology explanation**, submitted through HackOS. Reconfirm the authenticated final checklist before submission.

Judge-facing priorities: **Impact 30 / Technical 20 / Innovation 15 / Demo 15 / UX 10 / Sponsor Tech 10** (100 total). This rubric guides product tradeoffs; it is not permission to omit correctness, security, or mandatory sponsor integration.

## Dependency Setup

Declare this exact dependency in the consumer's existing `pyproject.toml` and update its lockfile:

```toml
[project]
dependencies = [
  "agentic-intent-gate @ git+https://github.com/miku-wwl/agentic-intent-gate.git@7261fdd2f47d2b15fabe8faac527eeee37338eb1",
]
```

**Merge the dependency entry**; do not replace an existing `[project]` section or other dependencies blindly. Verify the installed distribution reports `agentic-intent-gate==0.2.0`, resolves to the pinned source commit, and is imported from the installed environment, **not an adjacent source checkout**. Use the [v0.2.0 consumer handoff](https://github.com/miku-wwl/agentic-intent-gate/blob/main/docs/V0.2.0-CONSUMER-HANDOFF.md) and [v0.2.0 adapter guide](https://github.com/miku-wwl/agentic-intent-gate/blob/v0.2.0/docs/ADAPTER_GUIDE.md) as integration references, **but note that the handoff URL points to moving `main`**. Cross-check any handoff instruction against the **installed pinned commit** and its available tagged documentation; do not treat newer `main` instructions as v0.2.0 API guarantees.

## Reuse the Core

Within its supported scope, Agentic Intent Gate already provides:

- Strict structured Plan validation and trusted, bounded tool schemas.
- Persistent Runs and exact Plan-to-Approval binding.
- Independent Action execution Authorization, separate from Plan Approval.
- Explicit trusted single-tool `ToolExecutor` registration.
- Single-step `SIDE_EFFECT` Action lifecycle.
- SQLite-backed durable Action state, claim, audit events and receipt references.
- CAS/concurrency controls, stable effect keys, binding identity and idempotent command handling.
- Fail-closed recovery and terminal ambiguous/`Unknown` outcomes (no blind retry).
- Trusted configurable adapter execution budgets: default **5 seconds**, explicit maximum **15 seconds**.

**Do not copy, fork, reimplement, monkeypatch, or bypass these core mechanisms in the consumer.** Use the published public API and a fixed dependency revision.

## Public Integration Entry Point

Inspect the **installed v0.2.0 API** and the core repository's `examples/consumer/app.py` before implementing integration. Supported imports include:

```python
from agentic_intent_gate.runtime import (
    ToolBinding,
    ToolCapability,
    ExecutableRegistry,
    CapabilityVerifier,
    BoundCapabilityAuthorization,
    execution_budget_binding,
    open_runtime,
)
```

Check the actual constructor/function signatures; do not invent methods. Register trusted executors at startup with exact tool/version/target/adapter identity, reviewed binding revision, canonical execution scope, strict argument schema and appropriate independent authorization. Model output and untrusted HTTP input cannot register code or select trusted identities.

### Trusted Execution Budget (v0.2.0)

- `open_runtime(..., execution_timeout_seconds=5)` is the **backward-compatible default**. Finite built-in `int`/`float` values in `(0, 15]` are supported. Booleans, invalid types, NaN, infinity, non-positive values and values over 15 are rejected.
- For values **above 5**, trusted host code must explicitly opt in, use a **fresh reviewed base `ToolBinding` revision**, and apply `execution_budget_binding(base_binding, 15)` to produce a canonical binding revision ending in `.exec-15s`. The complete revision must fit the 64-character limit.
- Pass `execution_timeout_seconds=15` to `open_runtime` **only after the complete reviewed binding, capability, registry, verifier, policy and consumer effect/receipt identity are consistently configured**. Do not let model output, tool arguments, browser parameters, or API clients choose or increase this value.
- Keep the extended profile's binding revision, scope and persisted consumer configuration **stable across restarts**. Use a fresh UUIDv4 scope and **separate private gate/ledger/receipt-store identity** for a new extended profile.
- **Do not silently elevate old Actions or grants.** Never migrate, relabel, replay, or reuse legacy Approval, Authorization, effect keys or receipt identities under a longer budget. Create a new Plan/Run, obtain fresh human Approval, admit a new Action and obtain separate Authorization. Existing default-profile Actions retain their original identities; previously Failed/Unknown terminal Actions must not be reset or replayed.
- Extended Actions use `action-compiler-v3` / `action-spec-v3` and bind the reviewed budget profile into their identity. Old v1/v2 Actions cannot gain a longer budget merely by changing host configuration or using a similar binding name. Keep prior ledgers available for historical audit; v0.1.0 software cannot interpret v3 extended Actions.
- The configured adapter deadline starts **after durable Gateway claim**. The Gateway's synchronous claim and finish work are outside the adapter timer. A caller-supplied validated **monotonic** deadline may only **shorten**, never extend, this budget. Late outcomes, cancellation, lost acknowledgment and uncertain writes can still become `Unknown`.
- Provider requests, independent effect verification and adapter-side durable receipt persistence must fit within the adapter budget. External effects cannot necessarily be cancelled after dispatch. Avoid detached background execution, automatic retries, and recovery replay; **15 seconds is not a guaranteed completion time or exactly-once remote-effect guarantee**.
- The bundled Runtime Action HTTP routes retain a **10-second parent deadline**. If the consumer needs a full 15-second adapter allowance, use a supported public Gateway invocation within an appropriately budgeted **consumer-owned request envelope**; do not use private Runtime internals or assume the bundled HTTP endpoint grants 15 seconds.
- Consumer-specific constraints, including Sandbox-only execution, allowed targets, spend limits, HTTP timeouts, durable dispatch fencing and payment-provider policies, belong **in the consumer application**, not in the shared Runtime.

**Default rule:** Unless a reviewed use case needs an extended budget, omit the new argument and retain **5 seconds**.

## Product Architecture Boundary: Reasoning vs. Action

AIG v0.2.0 is the **side-effect governance boundary**, not the whole reasoning engine. The consumer application may have multiple **read-only reasoning/retrieval steps** outside AIG, subject to appropriate access control; it must not use those steps to perform unapproved effects.

Design the judge-visible happy path as:

`Zetaris context retrieval → Nemotron reasoning with cited evidence → proposed structured Plan → AIG validation/persistent Run → authenticated human Approval → Action admission → independent execution Authorization → bounded single trusted executor → independently checked effect and durable receipt → UI explanation`.

- **Zetaris queries and LLM reasoning** are consumer-owned stages, not undocumented AIG `READ_ONLY` tool calls.
- **One trusted SIDE_EFFECT executor per Runtime composition**, one step per Action; do not smuggle several arbitrary side-effect tools through one permissive dispatcher or generic shell/HTTP proxy.
- **Provider operation and verification** must fit the selected trusted adapter deadline. Keep the default **5-second** profile unless 15 seconds is demonstrably needed and the full reviewed extended-profile procedure below is followed.
- Prefer a **sandbox or non-destructive action** for the demo. If using a real external write, obtain explicit operation-specific owner authorization in addition to the application's proper end-user approval and separate execution authorization.
- Explain failures and refusal clearly. **Unknown is not Success**, and it must not cause an automatic second side effect.
- Do not put secrets or private user data into prompts, snapshots, trace exports, screenshots, or the demo video.

## Competition-Specific Responsibilities

Implement **only** the product-specific requirements:

1. Product concept, competition integrations, frontend and demo experience.
2. Trusted consumer tools, bounded argument schemas, concrete executors and receipt stores.
3. External service/API/MCP clients, where genuinely needed.
4. Consumer authentication, authorization, credentials and environment controls.
5. A suitable consumer `ModelProvider` when model-driven Plan generation is required.
6. Product tests, evaluation, deployment, documentation and submission.

**Demo boundaries:** The core's bundled local LLM prompt is tailored to `service-demo/service_id`, and its UI Action-admission controls remain Demo-specific. A non-Demo consumer must provide suitable planning and its own UI or use supported API admission paths; the bundled Demo UI does **not** automatically support arbitrary tools. The reference consumer's scripted approval is test/example consent, not proof of authenticated human approval.

## Supported Scope and Non-Goals

v0.2.0 supports **one explicitly registered trusted `SIDE_EFFECT` tool per Runtime composition and single-step execution**. It is **not** a general-purpose multi-agent engine. Do not assume general `READ_ONLY` tool execution, multi-tool/multi-step workflow orchestration, dynamic plugin discovery, arbitrary MCP execution, production multi-user authentication, distributed HA, malicious-Python isolation, or guaranteed exactly-once remote side effects.

If the competition requires unsupported functionality, identify the gap before building. Prefer a thin product-owned layer where safe. Request a separately reviewed core extension only when unavoidable; never silently bypass the core's safety gates.

## Mandatory Safety Boundaries

- Model output proposes a Plan; it **never** chooses trusted credentials, executors, scopes, execution budgets or grant decisions.
- Verify exact tool identity, schema, target, binding revision, execution scope and trusted profile before compilation and execution.
- **Human Approval and execution Authorization are separate gates**. Approval alone never dispatches an effect; do not fabricate or inherit consent from earlier Actions.
- Never substitute a different Plan's Approval, skip durable claiming, or weaken owner fencing and authorization checks.
- Treat ambiguous post-dispatch effects as `Unknown`; **no automatic retry, unsafe reconciliation, duplicate POST or recovery replay**. Distinguish proven pre-dispatch no-effect failures from uncertain remote effects.
- Respect the provider's documented idempotency semantics; a provider request ID is **not** a universal exactly-once guarantee.
- Keep secrets, capability tokens, private Git credentials, personal data and private state outside source, docs, screenshots and CI logs.
- Do not initiate real money movements, financial API mutations or other irreversible third-party effects without fresh, explicit, operation-specific human authorization.

## Acceptance Criteria

An external consumer using the exact pinned, **installed** package, **without modifying core source**, must demonstrate:

**Validated Plan → Persistent Run → Exact Human Approval → Admission → Independent Authorization → Durable Action Claim → Consumer Executor → Verified Effect → Durable Receipt**

Tests should cover successful execution and persistence; unknown tool, wrong target/binding/scope, missing authorization, stale approval, duplicate/concurrent/conflicting effects, and ambiguous outcome. For extended profiles, additionally test default/15-second configuration, invalid budgets, wrong-profile denial, old-Action non-escalation, shortening caller deadlines, pre-dispatch expiry, lost acknowledgments, late receipts and process restart/recovery **without a second effect**. Verify actual durable state rather than only printed success. Synthetic planning is acceptable for offline tests; genuine external side effects need separate permission.

## Product Quality Gates and Evidence

Every phase must ship **working, reviewable artifacts**, not only a plan:

1. **P0 (before kickoff):** Document official constraints and original-code reuse policy; verify install/source of AIG v0.2; validate environment and sponsor credentials with safe read-only smoke tests where permitted; outline one concrete use case and architecture. A blocked credential remains `BLOCKED`, not `PASS`.
2. **P1 (after kickoff):** Demonstrate **actual Zetaris retrieval + actual Nemotron inference** and a complete AIG-governed single-action vertical slice. Keep verified logs/tests and a browser-visible UI.
3. **P2:** Add denial/ambiguous-result cases, reproducible fixtures, performance/reliability measurements, UX polish, and independently inspected durable receipts. Compare claims to evidence; do not present synthetic tests as real-provider verification.
4. **P3:** Validate a deployed public demo if required by final rules, rehearse a 1–4 minute scenario, complete slides and README, document dependency reuse, sponsor evidence, known limitations, and submit on HackOS by the deadline.

For every completed task, report **`PASS`, `PARTIAL`, `BLOCKED`, `FAIL`, or `NOT_RUN`** with exact commands, relevant files, reproducible verification, and remaining blockers. No PASS based only on mocked responses, unrun tests, or console text that is not backed by durable state. Keep task scope small enough to show one end-to-end user outcome first; defer speculative features.

**Git / repo controls:** Inspect `git status` and existing files before edits; do not overwrite unrelated changes. Keep dependencies pinned and secrets out of the repository. Do not claim that a commit, push, deployment, external effect, registration, or submission happened unless a tool actually verified it. Ask for permission before paid resources, publishing, or irreversible third-party actions.

## Agent Work Protocol

Before changing code:

1. Read this `AGENTS.md`, other local instructions, the official event rules, and the current phase/build-window status.
2. Verify the exact pinned dependency, installed public API, package version and lockfile.
3. Read the shared Runtime's `examples/consumer/app.py`, v0.2.0 handoff and adapter guide; prefer pinned/tagged definitions over moving docs.
4. Check the actual Zetaris, Nemotron/Meterless and Cursor setup/evidence requirements for the task.
5. Propose and execute the smallest **consumer-specific** implementation with focused tests and a visible user outcome, within the authorized phase.
6. Flag missing capabilities, credentials, rule ambiguity and blockers rather than inventing public APIs, fabricating integrations or modifying the shared Runtime.

During development, preserve existing project state and security constraints. Keep changes scoped; use safe synthetic tests by default. **Do not commit, push, tag, release, deploy or run real external effects unless separately instructed.**

**Guiding rule: Build the Hackathon application; reuse the pinned Agentic Intent Gate Runtime.**
