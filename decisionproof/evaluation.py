"""Reproducible synthetic ablation. No live source/model or claimed business savings."""
import asyncio
import hashlib
import json
from pathlib import Path
import statistics
import time
from uuid import uuid4

from .contracts import Candidate, utc
from .ledger import decision_delta
from .reasoning import ReasoningLoop, facts, single
from .service import consumer,provision
from .sources import OfflineSource,SCENARIOS,scenarios


class SeverityBaseline:
    """Proposal sees only severity/KEV-like context; same independent safety validator."""
    def propose(self,snapshot):
        values = []
        for asset,group in sorted(facts(snapshot).items()):
            if not single(group,"kev_product"):
                continue
            score = single(group,"severity",0)
            values.append(Candidate(asset_id=asset,cve_id="CVE-2099-0001",score=score,
                evidence_ids=tuple(r.evidence_id for key in ("severity","kev_product") for r in group.get(key,[])),
                explanation=f"Limited-context severity priority {score}; applicability unconfirmed"))
        return tuple(sorted(values,key=lambda x:(-x.score,x.asset_id)))


def claim_metrics(decision,snapshot):
    lookup = {r.evidence_id:r for r in snapshot.active()}
    refs = [key for c in decision.ranking for key in c.evidence_ids]
    valid_refs = sum(key in lookup for key in refs)
    unsupported = sum(c.evidence_id not in lookup or (lookup[c.evidence_id].key,lookup[c.evidence_id].value,type(lookup[c.evidence_id].value)) != (c.field,c.value,type(c.value)) for c in decision.claims)
    return {"citation_count":len(refs),"valid_citations":valid_refs,"claim_count":len(decision.claims),"unsupported_claims":unsupported}


async def evaluate(root):
    rows = []
    for configuration in ("A_severity_only","B_full_no_followup","C_bounded_followup"):
        for spec in scenarios():
            started = time.perf_counter()
            directory = Path(root)/f"{configuration}-{spec['id']}-{uuid4()}"
            provision(directory,str(uuid4()))
            fault = {"unknown":"unknown","fail":"fail"}.get(spec["expected"]["execution"],"none")
            with consumer(directory,predecessor_stopped=True,fault=fault) as service:
                case = service.ledger.new_case(spec["id"])
                decision = await ReasoningLoop(service.ledger,OfflineSource(spec),
                    planner=SeverityBaseline() if configuration.startswith("A_") else None).run(case,followups=configuration.startswith("C_"))
                history = service.ledger.history(case)
                delta = decision_delta(history[0],decision,service.ledger.snapshot(history[0].snapshot_id),service.ledger.snapshot(decision.snapshot_id))
                state,commands = "No Action",0
                if decision.state == "READY_FOR_HUMAN_REVIEW":
                    plan = await service.propose(decision.decision_id);commands+=1
                    plan = service.approve(plan["run_id"],plan["version"],plan["review_fingerprint"]);commands+=1
                    action = service.admit(plan["run_id"],plan["version"],str(uuid4()));commands+=1
                    allow = spec["expected"]["execution"] != "deny"
                    action = service.authorize(action["action_id"],action["version"],str(uuid4()),allow);commands+=1
                    if allow:
                        action = await service.execute(action["action_id"],action["version"],str(uuid4()));commands+=1
                        state = action["state"]
                    else:
                        try:
                            await service.execute(action["action_id"],action["version"],str(uuid4()))
                            raise AssertionError("denied effect dispatched")
                        except ValueError:
                            state = "Denied"
                        commands+=1
                tasks = service.executor.tasks()
                integrity = len(tasks) <= 1
                if state == "Succeeded":
                    integrity = integrity and len(tasks)==1 and tasks[0]["receipt"]==action["result"]["receipt_reference"] and tasks[0]["decision_id"]==decision.decision_id
                elif state in ("Denied","Failed","No Action"):
                    integrity = integrity and not tasks
                elif state == "Unknown":
                    integrity = integrity and len(tasks)==1
                metrics = claim_metrics(decision,service.ledger.snapshot(decision.snapshot_id))
                rows.append({"configuration":configuration,"scenario_id":spec["id"],"category":spec["category"],
                    "expected":spec["expected"],"selection":decision.selected_asset,"state":decision.state,
                    "selection_correct":decision.selected_asset==spec["expected"]["selection"],
                    "appropriate_abstention":(decision.state=="ABSTAIN")== (spec["expected"]["selection"] is None),
                    "delta":delta,"revision_correct":delta["ranking_changed"]==(spec["expected"]["delta"]=="changed"),
                    "retrieval_rounds":decision.rounds,"task_state":state,"task_rows":len(tasks),"task_integrity":integrity,
                    "scripted_review_commands":commands,"elapsed_ms":round((time.perf_counter()-started)*1000,3),**metrics})
    summaries = {}
    for name in sorted({r["configuration"] for r in rows}):
        group = [r for r in rows if r["configuration"]==name]
        claims = sum(r["claim_count"] for r in group)
        refs = sum(r["citation_count"] for r in group)
        revision_cases = [r for r in group if r["expected"]["selection"] is not None]
        summaries[name] = {"scenarios":len(group),"selection_correct":sum(r["selection_correct"] for r in group),
            "appropriate_abstention":sum(r["appropriate_abstention"] for r in group),
            "citation_validity":sum(r["valid_citations"] for r in group)/refs if refs else None,
            "unsupported_fact_rate":sum(r["unsupported_claims"] for r in group)/claims if claims else None,
            "revision_correct":sum(r["revision_correct"] for r in revision_cases),"revision_cases":len(revision_cases),
            "retrieval_rounds":sum(r["retrieval_rounds"] for r in group),"task_integrity_passed":sum(r["task_integrity"] for r in group),
            "median_elapsed_ms":round(statistics.median(r["elapsed_ms"] for r in group),3),
            "scripted_review_commands":sum(r["scripted_review_commands"] for r in group)}
    return {"status":"PASS" if all(r["task_integrity"] for r in rows) else "FAIL","utc":utc(),
        "kind":"offline synthetic deterministic evaluation; automated consent, not owner human approval",
        "specification_sha256":hashlib.sha256(SCENARIOS.read_bytes()).hexdigest(),"summaries":summaries,"results":rows}


def main():
    root = Path(__file__).resolve().parents[1]
    result = asyncio.run(evaluate(root/".preflight/p1a-evaluation"))
    path = root/"docs/evidence/p1a/ablation-results.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result["summaries"],indent=2))


if __name__ == "__main__":
    main()
