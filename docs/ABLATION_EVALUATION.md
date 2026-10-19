# Offline ablation evaluation — actual results

Status: **PASS for executed synthetic comparison; live model/sponsor evaluation NOT_RUN**. Data: [raw results](evidence/p1a/ablation-results.json), [frozen scenarios](../fixtures/scenarios.json), [pre-engine specification/hash](evidence/p1a/scenario-specification.json). Run: `uv run --locked python -m decisionproof.evaluation`.

Sixteen expected outcomes were separately specified and frozen before engine implementation, across clear/misleading/irrelevant matches, missing version, exposure conflict, stale inventory, changed importance, missing maintenance, changed/unchanged recommendation, necessary abstention, denial, known failure and uncertain effect. All 16 ran under three configurations: **48 actual runs**. Expected outcomes were written by the same implementer, not an external/blinded evaluator; they were not changed after seeing the results. Fixture hash remains the pre-engine hash.

A restricts the proposer to KEV-like/severity context. The independent safety validator still checks available evidence and may abstain, so the baseline never bypasses action safety. B uses full initial context without follow-up. C uses full context and at most two permitted reads. All use deterministic code, synthetic facts, the same trusted sufficiency policy and real pinned AIG for any admitted task. No genuine model accuracy or actual sponsor performance is measured.

| Configuration | Correct choice incl. abstentions | Appropriate abstention | Revision expectation match | Total reads | Task integrity | Median ms | Scripted review commands |
|---|---:|---:|---:|---:|---:|---:|---:|
| A · severity-only proposer | 7/16 | 8/16 | 10/13 | 0 | 16/16 | 520.8 | 25 |
| B · full context, no follow-up | 10/16 | 10/16 | 10/13 | 0 | 16/16 | 542.5 | 35 |
| C · full context + bounded follow-up | 16/16 | 16/16 | 12/13 | 11 | 16/16 | 1175.3 | 65 |

All three configurations had 100% valid evidence references and zero unsupported **structured factual claims** in this run. This metric checks IDs/typed values against stored active evidence; it is not an expert semantic assessment of every explanatory sentence or a general hallucination benchmark. Scores and priorities are explicitly inferences, not vulnerability proofs.

C improves choice matching from 7/16 to 16/16 versus A and 10/16 to 16/16 versus B on these fixtures. It is slower and invokes more review commands because more cases reach an executable decision. No reduction in user effort/time or business savings is claimed. Elapsed times include local initialization/password hashing, evidence/ledger work and any scripted AIG execution, and vary with machine load. They exclude human deliberation.

Revision accuracy compares first-versus-final ranking change against frozen expectations in the 13 non-abstaining reference cases. **C matches 12/13**, not 13/13: s05 expected a reversal, but B was already first because the initial conflicting exposure contributes no affirmative exposure score. The new observation resolves that conflict without changing the ranking. The engine reports unchanged rather than manufacturing a reversal. Both old conflicting values remain in the Delta. s07 and s09 genuinely change rank; s10 genuinely confirms it.

Task integrity verifies at most one task, a correlated receipt for Succeeded, zero tasks for denial/known failure/abstention, and one retained task with Unknown for the deliberately lost-ack fixture. Tests use automated consent; the outcome is actual Runtime/SQLite state. Raw per-case decisions/digests/new evidence IDs/deltas, iterations, command counts and timings are retained. Broader crash/concurrency/security cases are in the test suite.

Browser interaction measurement: 10 control activations in the scripted hero flow including login/navigation/provenance inspection; 30 across the complete browser check. A normal minimal hero path is 8 clicks: login, analyze, execution tab, propose, approve, admit, authorize, execute. These are UI workflow counts, not a human productivity study. Baselines do not have separate user-facing UIs, so no comparative click-saving claim is made.

Limits: small synthetic set; same-author expectations; no held-out human study; deliberately simplified exact product match and heuristic ranking; conservative all-relevant-candidate sufficiency; no real vulnerability applicability finding. Repeat with independently reviewed cases, actual Zetaris context and genuine Nemotron, keeping all failures/abstentions and latency costs. Do not use 16/16 as a general accuracy or prize-winning claim.
