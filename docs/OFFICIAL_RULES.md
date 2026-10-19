# Official rules investigation — P0

Status: **PARTIAL**. Client date: 2026-10-20, Pacific/Auckland. Retrieval times are UTC in [public-sources.json](evidence/public-sources.json). Public-source verification is not authenticated organizer confirmation.

## Verified public findings

The [event's official rules](https://hackathon.genai.works/event/open-agent-hackathon-2026), sections 1–10, were read from the public server-rendered rules array; all ten section hashes were recorded. Findings:

| Topic | Public finding |
|---|---|
| Eligibility | Worldwide, age 16+ at kickoff; organizer/judging-sponsor employees cannot win cash; one account. Owner eligibility unconfirmed. |
| Teams | 1–5; solo allowed; one team/person; composition locks at first submission. Kiwi registration is owner-reported. |
| Tracks | One primary track. Track 3 concerns reliable decisions/actions from data, knowledge, memory and reasoning. |
| Window | 2026-10-22 00:00 → 2026-10-27 23:45 UTC. Earlier work needs pre-existing-component disclosure. |
| Reuse | Existing open-source libraries permitted; existing product code declared. Generated code permitted. |
| Stack, section 5 | Zetaris + Meterless + Cursor required; NVIDIA contribution encouraged. |
| Artifacts, section 6 | 1–4 minute video; slides; complete GitHub source/README; sponsor and Cursor explanation. |
| Judging | Impact/Technical/Innovation/Demo/UX/Sponsor: 30/20/15/15/10/10; three judges minimum. |
| IP | Entrant retains ownership; submission grants promotional licenses. |
| Hosting/visibility | No explicit public-hosting or public-repository clause found. Judge access requirements unresolved. |

## Conflicts and decisions on hold

**R-01 — BLOCKED: sponsor path.** The [Academy FAQ](https://academy.genai.works/courses/open-agent-hackathon-2026/details) requires Zetaris, Cursor and Nemotron, allowing direct Nemotron or Meterless. Event section 5 additionally mandates Meterless. Its final technology list is deferred to the Academy lesson *How the Week Runs: Tracks, Rules, Judging and Submission*. Do not lock a direct-only provider implementation. Prepare a design that can accommodate Nemotron through Meterless, but do not claim the public Meterless routing service proves the underlying model. Owner must obtain the authenticated lesson or organizer clarification explaining whether Meterless is mandatory and which model/provider paths qualify. This decision is stopped; independent P0 preparation continues.

**R-02 — PARTIAL: pre-existing AIG eligibility.** Public section 5 supports library reuse. AIG is owner-authored pre-existing infrastructure, so disclose it conservatively as both a pre-existing open-source dependency and pre-existing work by the entrant. Pin version/SHA, preserve MIT attribution, distinguish reused governance from newly built retrieval/reasoning/UI. Do not claim the framework as new hackathon work. Owner must confirm Track 3 accepts that reuse and what the submission form requires; Wildcard's existing-project rule does not establish Track 3 eligibility by itself. [Disclosure template](templates/REUSE_DISCLOSURE.md).

**R-03 — PARTIAL: dates/prize copy.** [Zetaris's earlier press release](https://www.zetaris.com/company/media-and-press/zetaris-launches-cloud-ai-data-harness-for-ai-agents) still advertises October 15–20. The current organizer page and repository agree on October 22–27, which controls this preparation boundary. Academy and event prize breakdowns also differ. Do not base eligibility or budget on old publicity. Recheck organizer announcements at kickoff.

## Authenticated facts still UNVERIFIED

Browser inventory returned no available browser; creating an IAB tab returned `Browser is not available: iab`. No login, account creation or private HackOS access occurred. Public rules were nevertheless read completely through HTTPS; the inaccessible part is the account workspace/lesson, not the public accordion.

| Missing fact | Exact owner verification action |
|---|---|
| Final stack, model allowlist, credit quotas, pre-event allowances | Open Academy's *How the Week Runs* and *Start Here* plus Data/Power Quick Starts; provide the relevant rule text or screenshots directly in chat. Never include keys. |
| Track 3 reuse treatment | Ask organizer whether `agentic-intent-gate==0.2.0`, MIT, SHA `7261fdd2f47d2b15fabe8faac527eeee37338eb1`, pre-built by the solo entrant, is allowed as declared infrastructure. No message was sent on owner's behalf. |
| Final form fields and evidence | Open Kiwi's HackOS submission form read-only; inspect required URLs, slide format, repository/judge access, hosting and visibility. Do not create a submission just to inspect it: team composition may lock. |
| Eligibility, IP and later changes | Owner reviews authenticated terms/announcements, confirms eligibility and any newer provisions. No terms were accepted. |

## Time and phase

Kickoff is **October 22, 13:00 NZDT**; deadline is **October 28, 12:45 NZDT**. Onboarding advertised by Academy is October 21, 12:00 UTC = October 22, 01:00 NZDT. UTC evidence on October 19 corresponds to the client's October 20 just after midnight in Auckland.

P0 consists only of research, preparation, dependency qualification and synthetic local checks. None of these artifacts is claimed as eligible in-window product development. No product implementation begins until kickoff, sponsor ambiguity is resolved, and a new P1 instruction authorizes the next phase.
