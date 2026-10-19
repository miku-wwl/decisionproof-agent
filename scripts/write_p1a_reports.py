"""Render concise reports from actual final local test/evaluation/browser evidence."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def main():
    evidence=ROOT/'docs/evidence/p1a'
    evaluation=json.loads((evidence/'ablation-results.json').read_text('utf-8'))
    browser=json.loads((evidence/'browser-result.json').read_text('utf-8'))
    suite=ET.parse(evidence/'all-tests.xml').getroot().find('testsuite')
    assert suite is not None
    count=int(suite.get('tests'));failed=int(suite.get('failures'))+int(suite.get('errors'))
    if failed or browser['status']!='PASS':
        raise SystemExit('Final verification is not PASS; do not generate a successful report')
    summaries=evaluation['summaries']
    rows=[]
    for label,identifier in [('A · severity-only proposer','A_severity_only'),('B · full context, no follow-up','B_full_no_followup'),('C · full context + bounded follow-up','C_bounded_followup')]:
        s=summaries[identifier]
        rows.append(f"| {label} | {s['selection_correct']}/16 | {s['appropriate_abstention']}/16 | {s['revision_correct']}/{s['revision_cases']} | {s['retrieval_rounds']} | {s['task_integrity_passed']}/16 | {s['median_elapsed_ms']:.1f} | {s['scripted_review_commands']} |")
    table='\n'.join(rows)
    ablation=f"""# Offline ablation evaluation — actual results

Status: **PASS for executed synthetic comparison; live model/sponsor evaluation NOT_RUN**. Data: [raw results](evidence/p1a/ablation-results.json), [frozen scenarios](../fixtures/scenarios.json), [pre-engine specification/hash](evidence/p1a/scenario-specification.json). Run: `uv run --locked python -m decisionproof.evaluation`.

Sixteen expected outcomes were separately specified and frozen before engine implementation, across clear/misleading/irrelevant matches, missing version, exposure conflict, stale inventory, changed importance, missing maintenance, changed/unchanged recommendation, necessary abstention, denial, known failure and uncertain effect. All 16 ran under three configurations: **48 actual runs**. Expected outcomes were written by the same implementer, not an external/blinded evaluator; they were not changed after seeing the results. Fixture hash remains the pre-engine hash.

A restricts the proposer to KEV-like/severity context. The independent safety validator still checks available evidence and may abstain, so the baseline never bypasses action safety. B uses full initial context without follow-up. C uses full context and at most two permitted reads. All use deterministic code, synthetic facts, the same trusted sufficiency policy and real pinned AIG for any admitted task. No genuine model accuracy or actual sponsor performance is measured.

| Configuration | Correct choice incl. abstentions | Appropriate abstention | Revision expectation match | Total reads | Task integrity | Median ms | Scripted review commands |
|---|---:|---:|---:|---:|---:|---:|---:|
{table}

All three configurations had 100% valid evidence references and zero unsupported **structured factual claims** in this run. This metric checks IDs/typed values against stored active evidence; it is not an expert semantic assessment of every explanatory sentence or a general hallucination benchmark. Scores and priorities are explicitly inferences, not vulnerability proofs.

C improves choice matching from 7/16 to 16/16 versus A and 10/16 to 16/16 versus B on these fixtures. It is slower and invokes more review commands because more cases reach an executable decision. No reduction in user effort/time or business savings is claimed. Elapsed times include local initialization/password hashing, evidence/ledger work and any scripted AIG execution, and vary with machine load. They exclude human deliberation.

Revision accuracy compares first-versus-final ranking change against frozen expectations in the 13 non-abstaining reference cases. **C matches 12/13**, not 13/13: s05 expected a reversal, but B was already first because the initial conflicting exposure contributes no affirmative exposure score. The new observation resolves that conflict without changing the ranking. The engine reports unchanged rather than manufacturing a reversal. Both old conflicting values remain in the Delta. s07 and s09 genuinely change rank; s10 genuinely confirms it.

Task integrity verifies at most one task, a correlated receipt for Succeeded, zero tasks for denial/known failure/abstention, and one retained task with Unknown for the deliberately lost-ack fixture. Tests use automated consent; the outcome is actual Runtime/SQLite state. Raw per-case decisions/digests/new evidence IDs/deltas, iterations, command counts and timings are retained. Broader crash/concurrency/security cases are in the test suite.

Browser interaction measurement: {browser['hero_control_activations_including_login_navigation']} control activations in the scripted hero flow including login/navigation/provenance inspection; {browser['total_control_activations']} across the complete browser check. A normal minimal hero path is 8 clicks: login, analyze, execution tab, propose, approve, admit, authorize, execute. These are UI workflow counts, not a human productivity study. Baselines do not have separate user-facing UIs, so no comparative click-saving claim is made.

Limits: small synthetic set; same-author expectations; no held-out human study; deliberately simplified exact product match and heuristic ranking; conservative all-relevant-candidate sufficiency; no real vulnerability applicability finding. Repeat with independently reviewed cases, actual Zetaris context and genuine Nemotron, keeping all failures/abstentions and latency costs. Do not use 16/16 as a general accuracy or prize-winning claim.
"""
    (ROOT/'docs/ABLATION_EVALUATION.md').write_text(ablation,encoding='utf-8')
    report=f"""# P1A v2 execution report — DecisionProof Agent / Kiwi

**Offline P1A: PASS. Competition/live submission readiness: PARTIAL.** Client date October 20, 2026, Pacific/Auckland. Early development permission is **OWNER_REPORTED**, without written organizer evidence; [scope record](EARLY_DEVELOPMENT_PERMISSION.md). This work is not asserted to be eligible in-window code.

## Implemented outcome

A working authenticated localhost Patch Review product now combines a bounded evidence loop, immutable Decision Ledger, structured Decision Delta, a three-screen UI and a genuine installed-AIG sandbox action. No earlier P1A application existed in the clean checkout; the P0 architecture was reused rather than replaced. No new execution/orchestration framework was introduced.

Hero s09 initially ranks A before B. Missing B exposure causes a permitted `asset_details(B)` read. Actual synthetic records establish B exposure and importance 2→5; the recomputed rank becomes **B,A**. The operator can inspect provenance, alternatives and applicability uncertainty, approve the exact Plan, admit an Action, independently authorize it and execute once. The real result is one persisted sandbox task with a correlated receipt. No patch/scan/exploit/external ticket write is implemented.

## Acceptance gates

| Gate | Status | Actual evidence |
|---|---|---|
| G1 Offline functional product | PASS | Authenticated local application and actual task/receipt |
| G2 Bounded reasoning/retrieval | PASS | Max two rounds, three-second offline deadline, typed allowlisted intentions, size/schema/conflict checks; [architecture](AGENT_REASONING_ARCHITECTURE.md) |
| G3 Evidence-backed changes | PASS | Structured s09 A→B and s07 change, s10 unchanged, conflict-preserving Delta; revision expectations 12/13 with retained s05 mismatch |
| G4 Persistent history | PASS | Immutable history checks; actual new server process reloads the same decisions/task |
| G5 Real pinned AIG v0.2 | PASS | Exact installed SHA/version/import, default five seconds, real approval/admission/authorization/claim/execution |
| G6 Duplicates/ambiguity | PASS | Exact replay/concurrency, failure/Unknown and child-process exit after commit; one task, one attempt, no recovery replay |
| G7 Actual browser E2E | PASS | {browser['browser']} / Playwright {browser['playwright']}, actual rendered UI and six screenshots, no JS page errors; scripted authenticated reviewer, not owner consent |
| G8 ≥12 executed scenarios | PASS | 16 frozen scenarios × 3 configurations = 48 runs |
| G9 Baseline/ablations | PASS | Choice matching 7/16 → 10/16 → 16/16, timing/citation/abstention/task metrics and limitations retained |
| G10 Sponsor-ready interfaces | PASS, normalized scope only | Typed context/planner/intention contracts and refusal tests; genuine vendor clients still BLOCKED |
| G11 Reproducible storyboard | PASS | [Approximately three-minute sequence](HERO_DEMO_STORYBOARD.md) matches actual browser workflow; narrated recording/rehearsal NOT_RUN |
| G12 No fabricated integrations | PASS | All current evidence/planning labeled synthetic/deterministic; live sponsors BLOCKED, Cursor NOT_RUN |

## Commands and verification

- `uv sync --locked --link-mode copy`; `uv lock --check --offline`; `uv pip check`: installed/locked Python environment compatible.
- `python -m pytest -q --junitxml=docs/evidence/p1a/all-tests.xml` with `P0_AIG_REFERENCE` set: **{count} passed, zero failures/errors** in the final full run. [JUnit](evidence/p1a/all-tests.xml).
- `python -m decisionproof.evaluation`: actual 48-run comparison. [Results](evidence/p1a/ablation-results.json), [analysis](ABLATION_EVALUATION.md).
- `python -m scripts.run_browser_check`: genuine browser success/denial/abstention/reload/new-server-history check in {browser['elapsed_seconds']} seconds; outside requests blocked, zero JS errors. This timing is automated execution, not a three-minute human demo.
- `node --check decisionproof/static/app.js`: syntax checked. Six actual screenshots were visually inspected for the evidence/decision/execution flow.
- Remote annotated tag again resolved to `7261fdd2f47d2b15fabe8faac527eeee37338eb1`; installed package version is 0.2.0 and resolves from .venv site-packages. The upstream tracked checkout remains unchanged. P0's RECORD check validates 57 hashes.

An earlier full run found a test assumption requiring exactly one read under a 20 ms overall deadline. It legitimately expired before dispatch and abstained with zero reads/effects. The test now verifies both valid fail-closed paths: pre-read expiry or cancellation of a started read. The product budget was not increased. [Deadline observation](evidence/p1a/deadline-case.json). The locked Starlette TestClient emits a deprecation warning about httpx; it is not a failure or a real-provider check. Interim results are not substituted for the final full suite.

## Explicit answers to the seven product questions

1. **More than a ranking chatbot:** it selects permitted evidence acquisition, records critique/revisions, computes a data-derived Delta, preserves history and produces a governed durable operational handoff. It remains a deterministic offline product, not demonstrated model reasoning.
2. **Actual adaptation:** critic gaps choose inventory versus policy reads or no read. New context is re-evaluated within two rounds/deadline; a forced reversal/scenario-transition script does not control the engine.
3. **Evidence that changed the hero choice:** B exposure unknown→true and business importance 2→5, with new immutable IDs and a superseded importance claim. Delta stores both ranks/digests/claims and generated explanation. s05 resolves conflict without changing the recommendation.
4. **Correct abstention:** missing/unresolved version or maintenance, conflict/staleness after budget exhaustion, no relevant product, ties, invalid planner references/schema, unauthorized retrieval intention or deadline. ABSTAIN cannot propose an executable Plan; no exception bypass exists.
5. **Measured benefit:** on these 16 synthetic specifications, choices match 7/16 baseline, 10/16 full initial context and 16/16 with follow-up. Revision expectation match is 12/13. C takes more time/commands; no business-saving/general-accuracy claim is made.
6. **Reliable action control:** real public AIG v0.2.0, fixed tool/target/scope/profile, exact persistent Plan approval, independent authorization, durable claim/CAS/effect identity, consumer uniqueness, independent receipt verification, terminal Unknown and no automatic uncertain-effect retry. Authenticated APIs and changed-decision guards surround the public integration; core is neither copied nor patched.
7. **Remaining live competition work:** obtain written early-development/reuse/technology rules, assigned Zetaris two-source access, approved/free Nemotron/Meterless route with underlying model proof, real response/evaluation/browser evidence, substantive Cursor development, user validation, narrated demo/slides/README refinement and any separately authorized hosting/submission.

## Delivery and repository state

Main code: `decisionproof/contracts.py`, `sources.py`, `reasoning.py`, `ledger.py`, `service.py`, `web.py`, CLI and local static UI. Fixtures/expected outcomes: `fixtures/scenarios.json`. Product/security tests and browser/evaluation scripts are included. Required additional documents are this report's linked architecture/Delta/storyboard/evaluation and [competition strategy](COMPETITION_SCORE_STRATEGY.md).

Review ZIP is generated by `python scripts/package_p1a.py`, with a SHA-256 sidecar and [package manifest](evidence/p1a/package-verification.json). It includes safe code, fixtures, reports and sanitized evidence/screenshots, not private credentials, sandbox databases, environments or server logs. No archived test context is reset; all demonstrations initialize fresh isolated contexts.

Initial/final HEAD remains `77664912cc2094f82eb2ce2169fcc056dd9215b1`; no changes are staged. Existing AGENTS.md/LICENSE and P0 reports remain historical and unchanged. README, consumer manifest/lock and new P1A files are local review changes. **No commit, push, tag, release, public deployment, sponsor call, paid usage, external device/service effect or HackOS submission was performed.**
"""
    (ROOT/'docs/P1A_EXECUTION_REPORT.md').write_text(report,encoding='utf-8')
    print(f'Wrote evidence-derived reports: {count} tests; 48 ablation runs; real Chromium PASS')


if __name__=='__main__':
    main()
