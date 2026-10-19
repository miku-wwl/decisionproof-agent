# Reproduce P1A verification

Status: results are in [all-tests.xml](evidence/p1a/all-tests.xml), [ablation-results.json](evidence/p1a/ablation-results.json) and [browser-result.json](evidence/p1a/browser-result.json). No sponsor/live-model performance is included.

```powershell
uv sync --locked --python 3.13 --link-mode copy
$env:P0_AIG_REFERENCE = 'C:\Users\weila\AppData\Local\uv\cache\git-v0\checkouts\c84b7b6455190ce3\7261fdd'
uv run --locked python -m pytest -q --junitxml=docs/evidence/p1a/all-tests.xml
uv run --locked python -m decisionproof.evaluation
uv run --locked python -m playwright install chromium
uv run --locked python -m scripts.run_browser_check
uv lock --check --offline
uv pip check
node --check decisionproof/static/app.js
uv run --locked python scripts/package_p1a.py
```

On another machine use the pinned external uv cache checkout path, or run just the two product test files when the P0 reference is not available. The full P0 harness verifies the reference SHA before reading it and imports the installed package only. No AIG source is copied into this consumer or patched.

Coverage includes sixteen separately specified outcomes; history/Delta/restart; strict query/batch/schema and deadline bounds; wrong tool/target/binding/scope; CVE identity and immutable evidence IDs; stale decision/Plan/version; missing and denied authorization; actual exact replay/concurrent/conflicting command behavior; failed/Unknown outcomes; receipt-store identity mismatch; a real child-process exit after task commit followed by fail-closed recovery; authentication/Origin/CSRF, schema rejection, sensitive-error redaction and login throttling. Direct SQLite mutation in negative tests targets only fresh test-owned consumer stores, never AIG core code or a real owner's history.

Chromium is a genuine software browser test, not an ASGI-only or fabricated screenshot. It uses scripted reviewer controls, not proof that the owner personally consented. Six screenshots are from actual rendered pages. One restarted server is verified only after the test's own previous process is terminated and joined. The browser context blocks all non-localhost requests. Test subprocesses and generated secrets remain in ignored private directories, outside the review ZIP.

JUnit hostname labels are redacted during packaging; test outcomes/timestamps/durations are preserved. A Starlette TestClient deprecation warning about httpx may appear with this locked environment; it is not a failure and does not justify changing the pinned shared runtime or inventing a new sponsor client. Package integrity checks use CRCs and SHA-256 plus explicit file/type allowlists and bounded credential-pattern scans; this is not an account-wide secret audit.
