# Decision Delta and persistent memory

Status: **PASS offline**, including restart and immutable-history checks.

`Ledger` stores cases/current pointers, immutable snapshots, immutable decisions, acquisition attempts, concise events, Run links and Action links. SQLite triggers reject UPDATE/DELETE of history. The mutable case pointer identifies the newest revision; it never changes earlier snapshots or approvals. This is application decision history, not another execution ledger: AIG alone owns Run/Approval/Authorization/claim/Action state.

`decision_delta(previous, current, old_snapshot, new_snapshot)` computes:

| Output | Calculation |
|---|---|
| Previous/current IDs and evidence digests | Read from the two persisted decisions/snapshots |
| Newly acquired evidence IDs | Current active-ID set minus previous active-ID set |
| Removed/superseded claims | Previous active-ID set minus current active-ID set |
| Changed fields | Newly active records whose typed field value differs from the previous value or conflicting value set |
| Previous/current ranking | Asset IDs in each structured candidate order |
| Changed assumptions | Actual set difference between stored assumption strings; empty if unchanged |
| Remaining uncertainty | Current structured decision uncertainty |
| Explanation | Generated from these differences, never an independently fabricated narrative |

Supersession must reference earlier records for the same asset and field. Original records remain in the immutable snapshot/history; active views exclude superseded IDs. Conflicting earlier values are preserved as a list in `before`, not silently replaced by the last observed value. UI provenance clicks identify source, field, observed time and synthetic/public status.

Hero s09: A initially outranks B. `asset_details(B)` supplies B exposure `unknown → true` and importance `2 → 5`, superseding the old importance claim. Ranking becomes **A,B → B,A**. All IDs/digests/source rows and the ranking comparison are in [raw evaluation](evidence/p1a/ablation-results.json). The explanation is generated from those structured changes.

s10 acquires maintenance context and keeps A first: UI says ranking unchanged. s05 resolves conflicting exposure to false, but B was already first under the conservative initial scoring. Its frozen expectation anticipated a ranking change; actual output does not force one. This retained mismatch accounts for the evaluation's 12/13 revision-expectation result.

The current UI compares first versus newest case revision, offers stored earlier-version summaries and reloads case history. `POST /api/cases/{id}/refresh` creates new immutable revisions and changes the current pointer. Every proposal/approval/admission/authorization/dispatch checks current decision identity plus evidence/decision association. If that pointer changed, old Plan contents remain unchanged, and the consumer refuses to reuse their approval/authorization for the new decision. A fresh decision → Plan → Approval → Authorization is required.

Synthetic counterfactual exploration creates a **separate case and separately labeled evidence snapshot**, setting the first fixture asset's hypothetical exposure to false. It never rewrites original observations, CISA records, terminal Actions or receipts. Counterfactual records are not real public evidence, and their label persists after restart. Demo reset means a newly initialized directory; no existing Unknown is reset or replayed.
