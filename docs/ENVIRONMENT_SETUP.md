# Reproducible P0 environment

Status: **PASS for local Python dependency/test setup; PARTIAL for full build environment**. Snapshot: [environment.json](evidence/environment.json), 2026-10-19T11:28:03Z / October 20 NZDT.

| Component | Observed | Status / limit |
|---|---|---|
| Host | Windows 11 Home Chinese, x64, OS 10.0.26200; PowerShell 7.6.7 | PASS; inspected, not assumed |
| Git | 2.49.0.windows.1 | PASS |
| Python | CPython 3.13.9 at `D:\anaconda3\python.exe` | PASS; `py` launcher absent, not needed |
| uv | 0.11.16 | PASS |
| Consumer environment | `.venv`, Python 3.13.9; 29 packages | PASS; no global Python changes |
| pytest | 9.1.1, locked dev dependency | PASS; five tests actually ran |
| Backend prerequisites | FastAPI 0.147.0, httpx 0.28.1, Uvicorn 0.54.0 transitively installed by AIG | PASS for installation; consumer server NOT_RUN |
| Frontend prerequisites | Node v26.5.0, npm 12.0.1 | PASS versions; no frontend dependencies/app were created |
| Docker | Client/Engine 29.8.0, `desktop-linux` | PASS inventory only; no image pull/container workload run |
| Cursor | No command/path/process/standard uninstall entry found in checked locations | BLOCKED usable access; installation absence not proven |
| Browser automation | No browsers available; IAB creation failed | BLOCKED browser verification; product UI NOT_RUN |
| Sponsor access | No matching configured environment names; tenant endpoint absent | BLOCKED actual query/inference |

## Commands executed

From `D:\workshop\oct\decisionproof-agent`:

```powershell
git status --short --branch
git ls-files
git log -1 --format='%H %cI %s'
uv python find 3.13
uv sync --python 3.13
& .\scripts\Invoke-P0Checks.ps1
```

The script performs `uv sync --locked --python 3.13 --link-mode copy`, `uv lock --check --offline`, `uv pip check`, discovers the pinned reference in uv's external cache, runs isolated dependency checks, inventories the host, and reads public source/catalog endpoints. It does not read keys, call inference, create sponsor resources, run Docker workloads or execute product features. Initial uv hardlink fallback was a performance warning due to cross-volume cache; the repeatable command uses copy mode. This is not an install failure.

Direct test command, if the cache location must be supplied explicitly:

```powershell
$env:P0_AIG_REFERENCE = 'C:\Users\weila\AppData\Local\uv\cache\git-v0\checkouts\c84b7b6455190ce3\7261fdd'
.\.venv\Scripts\python.exe -I -m pytest tests/preflight -q --junitxml=docs/evidence/p0-tests.xml
```

The example remains outside the consumer. On another machine use `Invoke-P0Checks.ps1 -AigReference <pinned-cache-checkout>`; never add its `src` to `PYTHONPATH`. The SHA is checked before the example loads. New synthetic private directories are used per test; no existing user data is removed. The script does not clean old verification stores; leave them ignored and out of archives.

To refresh only public connectivity evidence:

```powershell
.\.venv\Scripts\python.exe -I scripts/p0_public_sources.py
```

Public GET success is not sponsor-login success. The script rejects MPI access-challenge HTML even when its HTTP status is 200, validates CISA JSON fields/count, and records local Meterless connection failure without printing potentially sensitive error URLs/IPs.

## Configuration and evidence hygiene

`.env.example` contains only empty values and comments; no automatic environment loader or product config exists yet. When access is granted, configure secrets locally or in a private credential store. `.gitignore` excludes `.env*` except the template, `.venv`, `.preflight`, private SQLite stores and generated archives. Do not place AIG capability tokens, identity stores or session secrets under `docs/evidence`.

Environment-variable checks inspected names/presence only across Process/User/Machine. Common Cursor paths checked included `D:\Cursor`, `D:\Programs\Cursor`, `%LOCALAPPDATA%\Programs\cursor` and `C:\Program Files\Cursor`, plus standard uninstall registry keys/processes. No credential-manager extraction or broad private-file search was attempted.

Only preparation manifests, tests, scripts, reports and safe templates were added. Original tracked files are protected; final verification compares them with HEAD. No application module, product data, schema, server, UI, Docker deployment or sponsor adapter exists. To create the review ZIP after reviewing changes:

```powershell
.\.venv\Scripts\python.exe -I scripts/package_p0.py
```

The archive uses an explicit allowlist, scans for common credential patterns, tests CRCs and verifies SHA-256 of every entry. It excludes raw web snapshots, private synthetic stores, tokens, virtual environments and `.git`. See [package evidence](evidence/package-verification.json) after packaging. The raw public research snapshots, if retained by this session, reside in the machine TEMP directory and are not deliverables.
