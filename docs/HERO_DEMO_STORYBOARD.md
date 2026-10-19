# Hero demo — approximately three minutes

Status: **PASS for reproducible offline sequence; narrated three-minute recording/rehearsal NOT_RUN**. [Actual Chromium evidence](evidence/p1a/browser-result.json) executes the workflow; its automated timing is not a human presentation duration.

Start with the README's fresh private sandbox. Sign in before recording; never show password entry, private files, account panels or API keys. Use English product UI. State aloud: **“This is the offline synthetic demonstration. The AIG runtime is real; live sponsor data/model and Cursor qualification remain pending.”**

| Time | Screen and real interaction | Narrative / evidence |
|---|---|---|
| 0:00–0:20 | Evidence tab, S09, Analyze | “Which asset should a small business investigate first?” Explain severity alone misses operational context; all current records are synthetic. |
| 0:20–0:45 | Compare assets/provenance | A has a supported initial priority. B lacks exposure data. The independent critic identifies that gap and chooses a bounded inventory read, rather than guessing. Open one citation. |
| 0:45–1:20 | Decision, Before/After | Show A → B and actual acquired rows: B exposure unknown → true, business importance 2 → 5. Show evidence IDs/digest change, one follow-up, alternatives and remaining applicability uncertainty. No fabricated reversal. |
| 1:20–1:40 | Revision history | Inspect concise steps and earlier immutable revision. Explain that evidence changes create new decisions; prior approval cannot govern them. Counterfactual exploration, if shown, is a separate explicitly synthetic case. |
| 1:40–2:20 | Execution | Propose exact Plan; show asset/CVE/decision/evidence digest. Click Approve, Admit, separately Authorize, then Execute once. Explain that approval itself dispatches nothing. |
| 2:20–2:40 | Task and receipt | Show actual Succeeded, one persisted task and receipt; reload and select history. It is a local investigation handoff, not a vulnerability proof or patch. |
| 2:40–3:00 | S08 / S12, or prepared screenshots from their actual runs | Insufficient maintenance evidence means ABSTAIN and no Plan. Denied authorization means no task. Finish with the small synthetic baseline comparison and clear remaining sponsor work. |

If fitting both refusal cases needs more time, show one live and one actual captured screenshot while clearly labeling the latter. Do not present a screenshot as a new runtime execution. Every new recording uses a fresh sandbox, never resets Unknown or replays a terminal effect for drama. Do not invent live integrations, savings or Cursor work.

Reproduction without desktop automation:

```powershell
uv run --locked python -m scripts.run_browser_check
```

This starts only its own localhost child, uses actual Chromium UI controls with a generated test password, blocks external requests, captures six real screenshots, checks zero-task denial/zero-Run abstention, stops its server, restarts a new process and verifies persistent history. It then stops the test server/browser. No ongoing public demo or video recording is implied.
