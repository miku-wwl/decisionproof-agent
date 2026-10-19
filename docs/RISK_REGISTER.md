# P0 risk register

Status: **PARTIAL**. Risks below are open unless explicitly verified. Owner = Kiwi entrant unless marked engineering. No risk is resolved by a plan alone.

| ID / severity | Evidence or gap | Status | Next action / gate |
|---|---|---|---|
| R-01 Critical | Event rules require Meterless; Academy permits direct Nemotron. | BLOCKED | Owner obtains authenticated final stack rule. Stop provider-route lock until resolved. |
| R-02 High | Public rules permit open-source libraries; entrant-authored AIG reuse treatment for Track 3 not specifically confirmed. | PARTIAL | Owner discloses version/SHA/pre-existing authorship and confirms eligibility/form fields. |
| R-03 High | Older sponsor date copy differs; organizer may change schedule. | PARTIAL | Use current organizer UTC window, recheck announcements at kickoff; preserve dated P0 baseline. |
| R-04 Critical | No Zetaris endpoint/credential/free entitlement available in inspected configuration. | BLOCKED | Owner requests event tenant or approved local-image access; engineering runs bounded read-only query only after access/free quota established. |
| R-05 Critical | No genuine Nemotron request; model allowlist/credits/rate limits unknown. Meterless routing IDs do not identify the actual model. | BLOCKED | Owner supplies Power Quick Start and free access locally; engineering proves underlying model and captures one real request. No mock main demo. |
| R-06 High | Cursor usable location/account not established. | BLOCKED | Owner provides/installs Cursor; substantive in-window change, focused test and redacted evidence required. |
| R-07 High | No authenticated HackOS lesson/workspace or browser automation available. | BLOCKED | Owner provides rule excerpts/screenshots and inspects final submission fields; later establish a targetable browser for real UI evidence. |
| R-08 High | Public deployment/public repo/judge access unresolved. | PARTIAL | Confirm form requirement before selecting hosting. Prepare locally; publishing still needs separate authorization. |
| R-09 Medium | KEV source readable; inventory/policy intentionally synthetic; no target-user evaluation. | PARTIAL | Label fixtures; conduct a bounded manual-baseline evaluation in P2. Do not claim customer validation or quantified savings now. |
| R-10 High | KEV membership does not prove a device version is vulnerable. | PARTIAL | Preserve applicability uncertainty; require authoritative version evidence for stronger claims; review task can request investigation. Never auto-patch. |
| R-11 High | Evidence may be stale, contradictory or contain prompt injection. | NOT_RUN product tests | P1 immutable provenance/citation validation, bounded packet, source age and fail-closed changed-snapshot handling. |
| R-12 Critical | Approval and separate authorization could be conflated; core approval method is not human auth. | NOT_RUN product tests | Implement authenticated consumer routes, CSRF, server-only capability and three visible stages; deny unauthorized calls. |
| R-13 High | Cross-store commit/lost acknowledgment can leave a task despite Unknown. | PASS dependency behavior; product NOT_RUN | P0 observed exactly that with synthetic audit effect. Implement atomic task/receipt, independent read, no second dispatch; test crash recovery during P1/P2. |
| R-14 High | Multi-worker/ephemeral hosting breaks ownership or audit retention assumptions. | NOT_RUN | One long-lived worker, private persistent volume, supported owner fence and operator-controlled recovery. No silent predecessor attestation. |
| R-15 Medium | Five-second executor budget must include task write, independent verification and receipt. | NOT_RUN product timing | Keep local task effect; measure under load. Do not raise budget to hide slow code. Extended profile requires separate review/full tests. |
| R-16 High | Secrets/data may leak into traces, screenshots or archive. | PARTIAL | Empty templates, ignored private paths, names-only credential checks, allowlisted ZIP and local scan. No claim to scan external account stores. |
| R-17 Medium | Sponsor Postman link returned 404; endpoint/model docs can drift. | PARTIAL | Obtain assigned contract; pin actual versions; use cataloged identifier and save safe response/config evidence. |
| R-18 High | Solo scope/delivery slips. | PARTIAL | One CVE/product family and one task; freeze features after complete vertical slice; drop external ticket systems and elaborate UI frameworks. |
| R-19 Medium | P0 artifacts mistaken for eligible in-window product work or example consent mistaken for human approval. | PASS boundary documented | Keep source disclosure and P0 hashes; collect separate real P1 evidence. P0 does not establish entry eligibility. |

P0 can be reviewed now. **P1 sponsor-backed vertical-slice readiness is BLOCKED** until R-01/R-04/R-05/R-06 are addressed; a later genuine browser check is also needed. Documentation work and installed-dependency qualification do not close these blockers.
