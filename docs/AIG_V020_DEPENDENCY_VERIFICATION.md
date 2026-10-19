# AIG v0.2.0 dependency qualification

Status: **PASS for the bounded P0 checks below; product integration NOT_RUN**.

## Identity and installation

| Check | Actual evidence |
|---|---|
| Annotated remote tag | `v0.2.0` object `b193d38a4804725d44ca536a3bd9778679cc7b4c`; peeled commit `7261fdd2f47d2b15fabe8faac527eeee37338eb1`. [Tag output](evidence/aig-tag.txt). This verifies tag resolution, not a cryptographic signature. |
| Distribution | Installed `agentic-intent-gate==0.2.0`, Python 3.13.9. |
| Source | Installed `direct_url.json` requested revision and commit both equal the full SHA. [Metadata](evidence/aig-smoke.json). |
| Resolution | `.venv/Lib/site-packages/agentic_intent_gate/runtime.py`; isolated `python -I`, no adjacent source checkout or `PYTHONPATH` injection. |
| Manifest/lock | New root `pyproject.toml` and `uv.lock`; exact Git SHA, no branch dependency. No prior manifest existed. |
| Compatibility | `uv sync --locked --python 3.13 --link-mode copy`, `uv lock --check --offline`, `uv pip check`: successful; 29 installed packages compatible. |
| Installed bytes | 57 nonempty distribution RECORD hashes verified. [Record evidence](evidence/installed-record.json). |

The reference is read from uv's external Git cache, at the pinned commit. No AIG source/example was copied into this consumer, edited, monkeypatched or forked. The cache's `.ok` marker is untracked uv metadata; tracked upstream files remain unchanged.

## References inspected

- [Pinned consumer example](https://github.com/miku-wwl/agentic-intent-gate/blob/7261fdd2f47d2b15fabe8faac527eeee37338eb1/examples/consumer/app.py), SHA-256 `98e6fc2812fc009d34c5abf3249bf31e791752d572c4910388132b8d7060df88`.
- [Pinned adapter guide](https://github.com/miku-wwl/agentic-intent-gate/blob/7261fdd2f47d2b15fabe8faac527eeee37338eb1/docs/ADAPTER_GUIDE.md).
- [Pinned handoff](https://github.com/miku-wwl/agentic-intent-gate/blob/7261fdd2f47d2b15fabe8faac527eeee37338eb1/docs/V0.2.0-CONSUMER-HANDOFF.md) and [moving handoff](https://github.com/miku-wwl/agentic-intent-gate/blob/main/docs/V0.2.0-CONSUMER-HANDOFF.md). Main was fetched/read as advisory material. Installed/pinned definitions control. The handoff's Refund Sentinel instructions are not DecisionProof requirements, and its upstream test counts are not our results.

## Verified public integration surfaces

All imports below come from `agentic_intent_gate.runtime`. Full constructor and bound-method signatures are preserved in [aig-smoke.json](evidence/aig-smoke.json).

```python
ToolBinding(tool_name, tool_version, adapter_id, binding_revision, target, execution_scope)
ToolCapability(binding, description, input_schema, target_argument=None, semantic_rule=None)
ExecutableRegistry(executor=None, *, binding=None)
CapabilityVerifier(token=None, *, subject_id=None, binding=None, operations=())
BoundCapabilityAuthorization(verifier, *, policy_revision)
open_runtime(*, gate_path, provider, capability, registry, verifier, policy,
             predecessor_stopped=False, execution_timeout_seconds=5)
```

`ModelProvider.generate_plan(intent, *, tools, plan_schema, timeout_seconds) -> str` is async. `ToolExecutor.execute(spec, effect_key, context) -> ToolOutcome` is async. Actual flow uses `run_service.create(Intent(...))`, `run_service.decide(run_id, ApprovalDecisionRequest(...))`, `gateway.admit(AdmissionCommand(...), principal)`, `gateway.authorize(ActionCommand(...), principal)`, and `await gateway.execute(ActionCommand(...), principal, deadline=...)`. `runtime.actions.get(action_id)` and `runtime.runs.get(run_id)` read persisted state. No conceptual `approve_plan()`, generic READ_ONLY execution or arbitrary MCP API is assumed.

The example reaches AwaitingApproval at run version 4, approved at 5; admission starts Action version 1, authorization produces 2. Product code must use returned versions and exact reviewed Plan, not blindly hardcode these numbers. `run_service.decide` has no human-principal parameter: consumer authentication and CSRF protection are mandatory around that call.

## Executed smoke results

Command: `& .\scripts\Invoke-P0Checks.ps1` (includes isolated `python -I -m pytest tests/preflight -q --junitxml=docs/evidence/p0-tests.xml`). After adding reproducible RECORD verification and strengthening the denial assertion, the isolated test command was rerun: **5 passed in 16.98 seconds**, zero failures. [JUnit](evidence/p0-tests.xml), [assertion results](evidence/aig-smoke.json), [test harness](../tests/preflight/test_aig_dependency.py). Only the JUnit machine-hostname label is redacted; outcomes/timing are preserved.

| Scenario | Observed durable result | Status |
|---|---|---|
| Pin/version/import/default-budget | Exact installed SHA, site-packages import, default 5 seconds | PASS |
| Complete example + duplicate exact command + restart | Succeeded; one effect row; one attempt; four Action events; receipt matches; a new Python process reads Succeeded | PASS |
| Approval/admission without execution authorization | `ACTION_NOT_EXECUTABLE`; zero effects | PASS |
| Commit acknowledgment lost | Unknown despite one committed effect; exact replay preserves outcome; new Python process reads Unknown; still one attempt/effect | PASS |
| Unregistered tool proposal | Persisted PlanRejected; zero effects | PASS |

These are actual local SQLite effects with deterministic planning and **scripted example consent**. They prove neither Nemotron inference, Zetaris connectivity, authenticated human consent, browser operation nor a product workflow. Private synthetic stores/capability tokens remain under ignored `.preflight/private`; they are excluded from the review ZIP. JSON/JUnit evidence contains no capability tokens. SQL in the harness is read-only inspection of known tables, not an alternative execution implementation.

## Scope and outstanding qualification

Use one trusted tool and one SIDE_EFFECT step per composition; flat closed schema with 1–16 required scalar fields, explicit bounds, no nested objects/arrays/defaults/optional values. Schema and canonical arguments stay within 4 KiB. Retrieve and reason outside the execution boundary. Consumer owns auth, immutable evidence, data/provider clients, effect verification and durable receipts.

The default **5-second** profile is retained; no extended profile is provisioned. 15-second configuration, invalid-budget matrix, wrong profile/binding/scope/target, stale approvals, concurrent/conflicting effects, late receipts, interrupted-Executing recovery and shortening-deadline cases are **NOT_RUN in P0** and required as applicable during P1/P2. Process restart above tests terminal-state persistence, not kill-during-dispatch recovery. Unknown remains terminal with no retry/reconciliation. No guarantee of universal exactly-once remote effects or production multi-user isolation is claimed.
