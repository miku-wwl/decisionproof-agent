"""Bounded consumer reasoning, independent evidence critique and validation."""
import asyncio
import inspect
from datetime import timedelta
from uuid import uuid4

from .contracts import Candidate, Claim, Critique, Decision, Gap, RetrievalIntent, Snapshot, parse_time, utc, validate_batch


def facts(snapshot):
    grouped = {}
    for record in snapshot.active():
        grouped.setdefault(record.asset_id,{}).setdefault(record.key,[]).append(record)
    return grouped


def single(group, key, default=None):
    rows = group.get(key,[])
    values = {str(type(row.value)) + repr(row.value) for row in rows}
    return rows[-1].value if len(values) == 1 else default


def critique_evidence(snapshot):
    gaps,notes = [],[]
    for asset,group in sorted(facts(snapshot).items()):
        known, installed = single(group,"kev_product"), single(group,"product")
        if known is not None and installed is not None and known.casefold() != installed.casefold():
            notes.append(f"{asset}: product mismatch; no relevant KEV-like product evidence")
            continue
        for field in ("cve_id","kev_product","product","severity","version","exposed","criticality","maintenance"):
            rows = group.get(field,[])
            if not rows:
                gaps.append(Gap(asset_id=asset,field=field,kind="missing"))
            elif single(group,field) is None:
                gaps.append(Gap(asset_id=asset,field=field,kind="conflict"))
            elif field in ("product","version","exposed","criticality"):
                if any(parse_time(snapshot.as_of)-parse_time(row.provenance.observed_utc) > timedelta(days=30)
                       or parse_time(row.provenance.observed_utc) > parse_time(snapshot.as_of) for row in rows):
                    gaps.append(Gap(asset_id=asset,field=field,kind="stale"))
    return Critique(gaps=tuple(gaps),notes=tuple(notes))


class OfflinePlanner:
    def propose(self, snapshot):
        ranking = []
        for asset,group in sorted(facts(snapshot).items()):
            known,installed = single(group,"kev_product"),single(group,"product")
            if not known or not installed or known.casefold() != installed.casefold():
                continue
            severity = single(group,"severity",0)
            criticality = single(group,"criticality",0)
            exposed = single(group,"exposed",False)
            score = severity + 3*criticality + (6 if exposed else 0)
            exposure_text = str(single(group,"exposed")) if single(group,"exposed") is not None else "unknown/conflicting (no exposure score added)"
            criticality_text = str(single(group,"criticality")) if single(group,"criticality") is not None else "unknown (no importance score added)"
            ranking.append(Candidate(asset_id=asset,cve_id=single(group,"cve_id","unconfirmed"),score=score,
                evidence_ids=tuple(r.evidence_id for rows in group.values() for r in rows),
                explanation=f"Investigation score {score}: severity {severity}, business importance {criticality_text}, exposure {exposure_text}. Applicability unconfirmed."))
        return tuple(sorted(ranking,key=lambda c:(-c.score,c.asset_id)))


def select_followup(critique, snapshot):
    assets = set(facts(snapshot))
    ordered = sorted(critique.gaps,key=lambda g:({"conflict":0,"stale":1,"missing":2}[g.kind],g.field=="maintenance",g.asset_id,g.field))
    for gap in ordered:
        query = "maintenance_context" if gap.field == "maintenance" else "asset_details"
        if gap.field in ("cve_id","kev_product","severity"):
            continue  # No allowlisted KEV mutation/retrieval seam in this offline scope.
        intent = RetrievalIntent(query=query,asset_id=gap.asset_id)
        if intent.asset_id in assets:
            return intent
    return None


class PermittedRetrievalPlanner:
    def select(self, critique, snapshot):
        return select_followup(critique,snapshot)


def validate_intention(intent, critique):
    if not isinstance(intent,RetrievalIntent):
        raise ValueError("structured retrieval intention required")
    for gap in critique.gaps:
        query = "maintenance_context" if gap.field == "maintenance" else "asset_details"
        if gap.field not in ("cve_id","kev_product","severity") and gap.asset_id == intent.asset_id and query == intent.query:
            return
    raise ValueError("retrieval intention is unrelated to a permitted evidence gap")


def validate_decision(decision, snapshot):
    """Trusted code never accepts a planner assertion of evidence sufficiency."""
    if decision.evidence_digest != snapshot.digest or decision.snapshot_id != snapshot.snapshot_id:
        raise ValueError("decision not bound to snapshot")
    by_id = {r.evidence_id:r for r in snapshot.active()}
    for claim in decision.claims:
        record = by_id.get(claim.evidence_id)
        if record is None or (record.key,record.value,type(record.value)) != (claim.field,claim.value,type(claim.value)):
            raise ValueError("unsupported factual claim")
    for candidate in decision.ranking:
        if not candidate.evidence_ids or any(key not in by_id or by_id[key].asset_id != candidate.asset_id for key in candidate.evidence_ids):
            raise ValueError("invalid evidence citation")
        if candidate.cve_id != single(facts(snapshot).get(candidate.asset_id,{}),"cve_id"):
            raise ValueError("unsupported CVE identifier")
    critique = critique_evidence(snapshot)
    if decision.state == "READY_FOR_HUMAN_REVIEW":
        if critique.gaps or not decision.ranking or decision.selected_asset != decision.ranking[0].asset_id:
            raise ValueError("insufficient evidence for action")
        if len(decision.ranking)>1 and decision.ranking[0].score == decision.ranking[1].score:
            raise ValueError("unresolved priority tie")
        group = facts(snapshot).get(decision.selected_asset,{})
        if single(group,"kev_product") != single(group,"product"):
            raise ValueError("irrelevant product")
    elif decision.state == "ABSTAIN" and decision.selected_asset is not None:
        raise ValueError("abstention cannot select executable target")
    return True


class ReasoningLoop:
    MAX_ROUNDS = 2
    DEADLINE_SECONDS = 3.0

    def __init__(self, ledger, source, planner=None, *, deadline_seconds=3.0,retrieval_planner=None):
        if type(deadline_seconds) not in (int,float) or not 0 < deadline_seconds <= self.DEADLINE_SECONDS:
            raise ValueError("invalid trusted reasoning deadline")
        self.ledger,self.source,self.planner = ledger,source,planner or OfflinePlanner()
        self.retrieval_planner = retrieval_planner or PermittedRetrievalPlanner()
        self.deadline_seconds = deadline_seconds

    def step(self, case_id, state, summary):
        self.ledger.event(case_id,state,{"summary":summary})

    def build(self, case_id, snapshot, previous, ranking, critique, rounds, state, reason):
        assumptions = ("Installed-version vulnerability is unconfirmed; task requests investigation only.",)
        uncertainties = tuple(f"{g.asset_id}: {g.kind} {g.field}" for g in critique.gaps)
        if not uncertainties:
            uncertainties = ("Exact vulnerability applicability requires authoritative version assessment.",)
        claims = tuple(Claim(evidence_id=r.evidence_id,field=r.key,value=r.value) for r in snapshot.active())
        return Decision(decision_id=str(uuid4()),case_id=case_id,previous_decision_id=previous,
            snapshot_id=snapshot.snapshot_id,evidence_digest=snapshot.digest,created_utc=utc(),state=state,
            ranking=ranking,selected_asset=ranking[0].asset_id if ranking and state != "ABSTAIN" else None,
            critique=critique,claims=claims,assumptions=assumptions,uncertainties=uncertainties,rounds=rounds,summary=reason)

    async def run(self, case_id, *, followups=True):
        deadline = asyncio.get_running_loop().time()+self.deadline_seconds
        snapshot = self.source.initial()
        self.step(case_id,"INITIAL_CONTEXT",f"Loaded {len(snapshot.records)} labeled offline evidence records")
        previous = self.ledger.case(case_id)["current_decision"]
        rounds = 0
        forced_reason = None
        while True:
            self.step(case_id,"PROPOSE_CANDIDATES","Compare product relevance, exposure and business context")
            try:
                ranking = self.planner.propose(snapshot)
                if inspect.isawaitable(ranking):
                    ranking = await asyncio.wait_for(ranking,max(0.001,deadline-asyncio.get_running_loop().time()))
                if type(ranking) is not tuple or len(ranking)>16 or not all(isinstance(c,Candidate) for c in ranking):
                    raise ValueError("intermediate proposal schema rejected")
            except (ValueError,TypeError,TimeoutError):
                ranking = ()
                forced_reason = "Planner schema rejected; no executable proposal"
            critique = critique_evidence(snapshot)
            self.step(case_id,"CRITIQUE_EVIDENCE",f"Independent check found {len(critique.gaps)} missing, conflicting or stale fields")
            if asyncio.get_running_loop().time() >= deadline:
                forced_reason = "Overall reasoning deadline reached"
            try:
                intent = self.retrieval_planner.select(critique,snapshot)
                if inspect.isawaitable(intent):
                    intent = await asyncio.wait_for(intent,max(0.001,deadline-asyncio.get_running_loop().time()))
                if intent is not None:
                    validate_intention(intent,critique)
            except (ValueError,TypeError,TimeoutError):
                intent = None
                forced_reason = "Retrieval intention refused by trusted allowlist/gap validator"
            can_retrieve = followups and critique.gaps and rounds < self.MAX_ROUNDS and intent is not None and not forced_reason
            if can_retrieve:
                state,reason = "PROVISIONAL","Candidate ranking is provisional pending permitted evidence"
            else:
                tied = len(ranking)>1 and ranking[0].score == ranking[1].score
                state = "ABSTAIN" if critique.gaps or not ranking or forced_reason or tied else "READY_FOR_HUMAN_REVIEW"
                reason = forced_reason or ("Evidence remains insufficient or priority is tied; no executable Plan" if state == "ABSTAIN" else "Evidence supports one investigation priority; vulnerability applicability remains unconfirmed")
            decision = self.build(case_id,snapshot,previous,ranking,critique,rounds,state,reason)
            self.step(case_id,"VALIDATE_DECISION","Validate structured claims, citations and action eligibility independently")
            try:
                validate_decision(decision,snapshot)
            except ValueError:
                decision = self.build(case_id,snapshot,previous,(),critique,rounds,"ABSTAIN",
                    "Independent validator refused the proposed ranking or evidence references")
                validate_decision(decision,snapshot)
                can_retrieve = False
            self.ledger.save(decision,snapshot)
            previous = decision.decision_id
            if not can_retrieve:
                if decision.state == "READY_FOR_HUMAN_REVIEW" and asyncio.get_running_loop().time() >= deadline:
                    decision = self.build(case_id,snapshot,previous,ranking,critique,rounds,"ABSTAIN","Overall reasoning deadline reached before publication")
                    validate_decision(decision,snapshot)
                    self.ledger.save(decision,snapshot)
                self.step(case_id,decision.state,decision.summary)
                return decision
            self.step(case_id,"SELECT_PERMITTED_FOLLOWUP",f"Read {intent.query} for asset {intent.asset_id}")
            self.step(case_id,"RETRIEVE_EVIDENCE","Execute one normalized allowlisted read; no SQL/code from planner")
            rounds += 1
            try:
                batch = await asyncio.wait_for(self.source.retrieve(intent,snapshot),max(0.001,deadline-asyncio.get_running_loop().time()))
                validate_batch(intent,batch,snapshot)
                snapshot = Snapshot.build(snapshot.records+batch.records,snapshot.as_of)
                self.ledger.acquisition(case_id,{"round":rounds,"intent":intent.model_dump(),"status":"RETURNED",
                    "evidence_ids":[r.evidence_id for r in batch.records],"provider":batch.provider})
            except Exception as error:
                forced_reason = "Retrieval refused or timed out: "+type(error).__name__
                self.ledger.acquisition(case_id,{"round":rounds,"intent":intent.model_dump(),"status":"REFUSED","reason":type(error).__name__})
            self.step(case_id,"REVISE_DECISION","Recompute candidates from the new immutable snapshot; never force a reversal")


def require_current(ledger, decision_id):
    decision = ledger.decision(decision_id)
    if ledger.case(decision.case_id)["current_decision"] != decision_id:
        raise ValueError("Evidence/decision changed; fresh Plan, Approval and Authorization required")
    if decision.state != "READY_FOR_HUMAN_REVIEW":
        raise ValueError("ABSTAIN/provisional decisions cannot create a Plan")
    validate_decision(decision,ledger.snapshot(decision.snapshot_id))
    return decision
