# Product selection — provisional recommendation

Status: **PASS for three-option evaluation and a documented recommendation; user research and product implementation NOT_RUN**. Scores are engineering judgment, not measured market impact or predicted judging scores. Final track/route decisions remain subject to R-01/R-02.

## Three bounded concepts

| Dimension | A. Recall Review | B. Patch Review — recommended | C. Invoice Exception Review |
|---|---|---|---|
| Target user | Owner-manager of one small grocery store | One IT generalist maintaining a small business's exposed appliances/services | One bookkeeper for a small supplier |
| Specific problem | Determine which stock lots need human recall investigation | Decide which one known-exploited-product exposure deserves a maintenance review today | Resolve one invoice/receipt/PO discrepancy before payment review |
| Context | Public MPI recall notice + synthetic lot/stock CSV + shop policy | Real CISA KEV catalog + synthetic asset inventory + maintenance policy | Synthetic invoice/PO/receipt and supplier-rule tables |
| Zetaris purpose | Query recall/stock/supplier sources together | Retrieve KEV facts, asset exposure/ownership, and maintenance policy from separate registered sources | Join three operational documents and policy context |
| Nemotron purpose | Explain ambiguous brand/lot/date relationships and missing evidence | Weigh known exploitation, asset importance, exposure, evidence gaps and maintenance constraints; cite facts and recommend one review | Explain quantity/price/timing conflicts and alternatives with citations |
| Single AIG action | Create one internal recall-investigation task | Create one local sandbox patch-review task with pinned evidence | Create one local sandbox accounts-payable review task |
| 1–4 minute story | Similar product, different batch → investigate one lot → reviewed task/receipt | Multiple alerts → compare one exposed asset with irrelevant/unknown candidates → approve a cited priority → one task/receipt | Plausible invoice → conflicting receipt → explain discrepancy → one exception task |
| Scope | One store, one notice, a few lots | One organization, one CVE/product family, a few assets, one task | One PO, one invoice, one receipt |
| Main risk | Current direct fetch returns an access challenge; real lot records unavailable | KEV alone does not prove the installed version is affected; no real business inventory/user validation | No real de-identified accounting evidence; heavily synthetic value demonstration |

Public source checks: [MPI recalls](https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/recalled-food-products) was BLOCKED despite HTTP 200; [CISA JSON](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json) actually parsed 1,748 records with required fields. These are standalone data-readiness checks, not sponsor integration. See [source evidence](evidence/public-sources.json). No private stock, finance or asset data was acquired.

## Scoring

Scale 1–5, where 5 is strongest. Score = sum(weight × rating) / 5. Weights express this solo project's priorities and are distinct from the official rubric.

| Criterion | Weight | A Recall | B Patch | C Invoice |
|---|---:|---:|---:|---:|
| Impact potential | 20 | 5 | 4 | 4 |
| Technical differentiation | 15 | 4 | 4 | 3 |
| Innovation | 10 | 4 | 3 | 3 |
| Sponsor depth | 15 | 5 | 5 | 5 |
| Six-day feasibility | 15 | 3 | 5 | 4 |
| Available verifiable data | 10 | 2 | 5 | 2 |
| Demo clarity | 10 | 5 | 5 | 4 |
| AIG v0.2 compatibility | 5 | 5 | 5 | 5 |
| **Total /100** | **100** | **83** | **89** | **75** |

Recall has stronger intuitive impact, but access barriers cost too much of this build window. Invoice review relies most heavily on invented business documents. Patch Review has a genuine machine-readable primary source available now and a clear small-team operational outcome. The novelty is evidence-linked choice under conflicting context and a verifiable handoff into a maintenance queue; governance serves that user outcome.

## Recommended vertical slice

Keep the working application name **DecisionProof Agent**. Scenario: **“Which exposed asset should I investigate first, and why?”** An IT generalist reviews a small catalog of synthetic assets. Actual Zetaris retrieval supplies public KEV facts and separate asset/policy context. Genuine Nemotron reasoning returns one recommended maintenance-review task, alternatives, source references and uncertainty. The operator approves that exact Plan, separately authorizes its Action, and executes it once. The result is a real durable task in a **local sandbox queue**, with an independently read receipt and reloadable audit view.

Do not call a KEV product-name match a confirmed affected installed version. Unless a retrieved authoritative advisory proves the exact version mapping, label applicability **unconfirmed** and create an *investigation* task. Missing version/exposure data must be visible. CISA dates are source facts, not deadlines imposed on this small business. No exploit scanning, network probing of assets, patch installation, device changes, emails, Jira writes or money movement belongs in this slice.

Fixtures are designed in P1, not created now: one relevant product/exposure, one misleading vendor-only match, one missing-version case; synthetic owner/maintenance information. The UI must identify those rows as synthetic even while the sponsor query and model inference are real. P0 did not select a live vulnerable device or construct product datasets.

## Success measures and limits

Measure task completion steps/time in a small evaluation with the same evidence and a documented manual baseline; no performance claim exists yet. P1 acceptance requires citations resolving to stored rows, visible missing evidence, a justified alternative comparison, one authorized task, and a durable correlated receipt. P2 should compare full reasoning against an ablation that omits asset/policy context, using a small held-out set and independent expected decisions. Deterministic freshness, schema and access checks constrain the model; free-form reasoning must not choose execution authority.

Defer fleet-wide scanning, automated remediation, external ticket systems, vector databases, agent swarms, real customer data and broad multi-tenant deployment. If no actual Zetaris/Nemotron route is available early on day 1, sponsor readiness stays BLOCKED; offline fixtures support tests only and cannot stand in for the main demonstration.
