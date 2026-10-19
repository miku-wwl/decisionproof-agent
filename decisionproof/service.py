"""Product composition through installed AIG public API; one sandbox task executor."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
from contextlib import closing, contextmanager
from uuid import UUID, uuid4

from agentic_intent_gate.runtime import (
    ActionCommand, AdmissionCommand, ApprovalChoice, ApprovalDecisionRequest, BoundCapabilityAuthorization,
    CapabilityVerifier, ExecutableRegistry, EXTERNAL_PAYLOAD_REVISION, Intent, Outcome,
    ToolBinding, ToolCapability, ToolOutcome, open_runtime, provision_capability,
)

from .contracts import canonical, sha, utc
from .ledger import Ledger, decision_delta
from .reasoning import ReasoningLoop, require_current
from .sources import OfflineSource, scenario

ARGUMENT_SCHEMA = {"type":"object","additionalProperties":False,
    "required":["asset_id","cve_id","decision_id","evidence_digest"],
    "properties":{"asset_id":{"type":"string","minLength":1,"maxLength":32},
        "cve_id":{"type":"string","minLength":1,"maxLength":32},
        "decision_id":{"type":"string","minLength":36,"maxLength":36},
        "evidence_digest":{"type":"string","minLength":64,"maxLength":64}}}


def binding_for(scope):
    return ToolBinding("create_patch_review","1","local-review-queue","patch-review-v1","sandbox-maintenance-queue",scope)


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),240000).hex()


def provision(directory, password):
    directory = Path(directory).resolve()
    if len(password) < 12:
        raise ValueError("Use a unique local password of at least 12 characters")
    directory.mkdir(parents=True,exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError("Initialize only a fresh empty sandbox directory; existing history is never reset")
    os.chmod(directory,0o700)
    binding = binding_for(str(uuid4()))
    (directory/"identity.json").write_text(canonical(vars(binding)),encoding="utf-8")
    salt = secrets.token_hex(16)
    (directory/"auth.json").write_text(canonical({"salt":salt,"hash":password_hash(password,salt)}),encoding="utf-8")
    provision_capability(directory/"capability")
    Ledger(directory/"decisions.sqlite3").provision()
    with closing(sqlite3.connect(directory/"tasks.sqlite3")) as db:
        db.executescript("""
        CREATE TABLE identity(binding TEXT NOT NULL);
        CREATE TABLE tasks(effect_key TEXT PRIMARY KEY, payload_digest TEXT NOT NULL,
            receipt TEXT NOT NULL UNIQUE, decision_id TEXT NOT NULL UNIQUE, body TEXT NOT NULL);
        CREATE TRIGGER immutable_tasks_update BEFORE UPDATE ON tasks BEGIN SELECT RAISE(ABORT,'immutable task'); END;
        CREATE TRIGGER immutable_tasks_delete BEFORE DELETE ON tasks BEGIN SELECT RAISE(ABORT,'immutable task'); END;
        """)
        db.execute("INSERT INTO identity VALUES(?)",(canonical(vars(binding)),))
        db.commit()
    for path in directory.iterdir():
        os.chmod(path,0o600)
    return directory


class DecisionPlanProvider:
    """Explicit offline deterministic planner, never labeled Nemotron."""
    def __init__(self, ledger):
        self.ledger = ledger

    async def generate_plan(self, intent, *, tools, plan_schema, timeout_seconds):
        if not intent.text.startswith("Decision "):
            raise ValueError("Only a persisted reviewed decision can propose a task")
        identifier = intent.text.removeprefix("Decision ")
        if str(UUID(identifier)) != identifier:
            raise ValueError("invalid decision identity")
        decision = require_current(self.ledger,identifier)
        candidate = decision.ranking[0]
        return canonical({"goal":"Create one sandbox investigation task; applicability unconfirmed",
            "target":"sandbox-maintenance-queue","risk_class":"SIDE_EFFECT",
            "steps":[{"tool_name":"create_patch_review","tool_version":"1","arguments":{
                "asset_id":candidate.asset_id,"cve_id":candidate.cve_id,"decision_id":identifier,"evidence_digest":decision.evidence_digest}}]})


class ReviewTaskExecutor:
    def __init__(self, directory, binding, ledger, *, fault="none"):
        if fault not in ("none","fail","unknown","crash"):
            raise ValueError("invalid trusted test fault")
        self.directory,self.binding,self.ledger,self.fault = Path(directory),binding,ledger,fault

    def tasks(self):
        path = self.directory/"tasks.sqlite3"
        with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=1)) as db:
            return [json.loads(row[0]) for row in db.execute("SELECT body FROM tasks ORDER BY rowid")]

    async def execute(self, spec, effect_key, context):
        def outcome(category,receipt=None,reason=None):
            return ToolOutcome(category,effect_key,spec.execution_scope,spec.target,spec.payload_digest(),receipt,reason)
        try:
            args = dict(spec.arguments)
            if not self.binding.matches(spec) or spec.identity_revision != EXTERNAL_PAYLOAD_REVISION or set(args) != set(ARGUMENT_SCHEMA["required"]):
                return outcome(Outcome.CONFIRMED_FAILURE,reason="INPUT_REJECTED")
            if str(UUID(effect_key,version=4)) != effect_key or str(UUID(context.attempt_id,version=4)) != context.attempt_id:
                return outcome(Outcome.CONFIRMED_FAILURE,reason="INPUT_REJECTED")
            decision = require_current(self.ledger,args["decision_id"])
            top = decision.ranking[0]
            if args != {"asset_id":top.asset_id,"cve_id":top.cve_id,"decision_id":decision.decision_id,"evidence_digest":decision.evidence_digest}:
                return outcome(Outcome.CONFIRMED_FAILURE,reason="INPUT_REJECTED")
            if self.ledger.denied(decision.decision_id) or self.fault == "fail":
                return outcome(Outcome.CONFIRMED_FAILURE,reason="INPUT_REJECTED")
            if context.expired():
                return ToolOutcome(Outcome.UNKNOWN_OUTCOME)
        except (ValueError,KeyError,TypeError):
            return outcome(Outcome.CONFIRMED_FAILURE,reason="INPUT_REJECTED")
        try:
            path = self.directory/"tasks.sqlite3"
            payload = spec.payload_digest()
            with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=rw",uri=True,timeout=1)) as db:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT binding FROM identity").fetchall() != [(canonical(vars(self.binding)),)]:
                    return outcome(Outcome.CONFIRMED_FAILURE,reason="STORE_IDENTITY_MISMATCH")
                row = db.execute("SELECT payload_digest,receipt FROM tasks WHERE effect_key=?",(effect_key,)).fetchone()
                if row:
                    return outcome(Outcome.SUCCESS,receipt=row[1]) if row[0] == payload else outcome(Outcome.CONFIRMED_FAILURE,reason="PAYLOAD_CONFLICT")
                if db.execute("SELECT 1 FROM tasks WHERE decision_id=?",(decision.decision_id,)).fetchone():
                    return outcome(Outcome.CONFIRMED_FAILURE,reason="PAYLOAD_CONFLICT")
                receipt = str(uuid4())
                task = {"task_id":str(uuid4()),"receipt":receipt,"effect_key":effect_key,"payload_digest":payload,
                    "decision_id":decision.decision_id,"asset_id":top.asset_id,"cve_id":top.cve_id,
                    "evidence_digest":decision.evidence_digest,"execution_scope":spec.execution_scope,"target":spec.target,
                    "created_utc":utc(),"status":"Open investigation","sandbox":True,
                    "title":f"Investigate {top.asset_id}; installed-version applicability unconfirmed"}
                db.execute("INSERT INTO tasks VALUES(?,?,?,?,?)",(effect_key,payload,receipt,decision.decision_id,canonical(task)))
                if context.expired():
                    db.rollback()
                    return ToolOutcome(Outcome.UNKNOWN_OUTCOME)
                db.commit()
            if self.fault == "crash":
                os._exit(91)  # Trusted fault injection only in an isolated test child, never HTTP-configurable.
            if self.fault == "unknown":
                return ToolOutcome(Outcome.UNKNOWN_OUTCOME)
            with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=1)) as verify:
                row = verify.execute("SELECT payload_digest,receipt,body FROM tasks WHERE effect_key=?",(effect_key,)).fetchone()
            if row != (payload,receipt,canonical(task)) or context.expired():
                return ToolOutcome(Outcome.UNKNOWN_OUTCOME)
            return outcome(Outcome.SUCCESS,receipt=receipt)
        except Exception:
            # Post-dispatch/commit uncertainty cannot be converted to a safe retry.
            return ToolOutcome(Outcome.UNKNOWN_OUTCOME)


@contextmanager
def consumer(directory, *, predecessor_stopped=False, fault="none"):
    directory = Path(directory).resolve()
    identity = json.loads((directory/"identity.json").read_text("utf-8"))
    binding = binding_for(identity["execution_scope"])
    if identity != vars(binding):
        raise ValueError("trusted profile identity mismatch")
    ledger = Ledger(directory/"decisions.sqlite3")
    capability = ToolCapability(binding,"Create one sandbox patch investigation task",ARGUMENT_SCHEMA)
    verifier = CapabilityVerifier((directory/"capability").read_text("ascii"),subject_id="sandbox-owner",binding=binding,
        operations=("read","admit","authorize","execute"))
    executor = ReviewTaskExecutor(directory,binding,ledger,fault=fault)
    with open_runtime(gate_path=directory/"gate.sqlite3",provider=DecisionPlanProvider(ledger),capability=capability,
        registry=ExecutableRegistry(executor,binding=binding),verifier=verifier,
        policy=BoundCapabilityAuthorization(verifier,policy_revision="patch-review-policy-v1"),
        predecessor_stopped=predecessor_stopped) as runtime:
        principal = verifier.verify("Bearer "+(directory/"capability").read_text("ascii"))
        yield Service(ledger,runtime,executor,principal)


class Service:
    def __init__(self,ledger,runtime,executor,principal):
        self.ledger,self.runtime,self.executor,self.principal = ledger,runtime,executor,principal

    async def analyze(self, identifier, *, case_id=None, counterfactual=False):
        spec = scenario(identifier)
        if case_id is not None:
            old = self.ledger.case(case_id)
            if old["scenario_id"] != identifier or counterfactual:
                raise ValueError("invalid case refresh")
        else:
            case_id = self.ledger.new_case(identifier,"synthetic counterfactual" if counterfactual else "original")
        result = await ReasoningLoop(self.ledger,OfflineSource(spec,counterfactual=counterfactual)).run(case_id)
        return self.case_view(case_id)

    async def propose(self,decision_id):
        decision = require_current(self.ledger,decision_id)
        runs,_ = self.ledger.links(decision.case_id)
        for identifier in runs:
            if self.ledger.run_decision(identifier).decision_id == decision_id:
                return self.run_view(identifier)
        run = await self.runtime.run_service.create(Intent("Decision "+decision_id))
        self.ledger.link_run(run.run_id,decision_id)
        self.ledger.event(decision.case_id,"PLAN_PROPOSED",{"run_id":run.run_id},decision_id)
        return self.run_view(run.run_id)

    def run_view(self,identifier):
        run = self.runtime.runs.get(identifier)
        plan = None if run.plan is None else {"goal":run.plan.goal,"target":run.plan.target,"risk_class":run.plan.risk_class.value,
            "steps":[{"tool_name":s.tool_name,"tool_version":s.tool_version,"arguments":dict(s.arguments)} for s in run.plan.steps]}
        return {"run_id":identifier,"state":run.state.value,"version":run.version,"plan":plan,"review_fingerprint":sha(plan)}

    def approve(self,run_id,version,fingerprint,approve=True):
        decision = self.ledger.run_decision(run_id)
        require_current(self.ledger,decision.decision_id)
        view = self.run_view(run_id)
        if not hmac.compare_digest(view["review_fingerprint"],fingerprint):
            raise ValueError("shown Plan changed")
        self.runtime.run_service.decide(run_id,ApprovalDecisionRequest(ApprovalChoice.APPROVE if approve else ApprovalChoice.REJECT,version))
        self.ledger.event(decision.case_id,"HUMAN_APPROVED" if approve else "HUMAN_REJECTED",{"run_id":run_id,"subject":"sandbox-owner"},decision.decision_id)
        return self.run_view(run_id)

    def admit(self,run_id,version,key):
        decision = self.ledger.run_decision(run_id)
        require_current(self.ledger,decision.decision_id)
        result = self.runtime.gateway.admit(AdmissionCommand(run_id,version,self.principal.subject_id,key),self.principal)
        self.ledger.link_action(result.action.action_id,run_id)
        return self.action_view(result.action.action_id)

    def authorize(self,action_id,version,key,allow=True):
        decision = self.ledger.action_decision(action_id)
        require_current(self.ledger,decision.decision_id)
        if self.ledger.denied(decision.decision_id):
            raise ValueError("Authorization was denied; a fresh decision is required")
        if allow:
            self.runtime.gateway.authorize(ActionCommand(action_id,version,key),self.principal)
        self.ledger.event(decision.case_id,"EXECUTION_AUTHORIZED" if allow else "AUTHORIZATION_DENIED",{"action_id":action_id,"subject":"sandbox-owner"},decision.decision_id)
        return self.action_view(action_id)

    async def execute(self,action_id,version,key,*,deadline=None):
        decision = self.ledger.action_decision(action_id)
        require_current(self.ledger,decision.decision_id)
        if self.ledger.denied(decision.decision_id):
            raise ValueError("Authorization denied; zero dispatch permitted")
        result = await self.runtime.gateway.execute(ActionCommand(action_id,version,key),self.principal,deadline=deadline)
        self.ledger.event(decision.case_id,"EXECUTION_RESULT",{"action_id":action_id,"state":result.action.state.value,"replayed":result.replayed},decision.decision_id)
        return self.action_view(action_id) | {"replayed":result.replayed}

    def action_view(self,identifier):
        action = self.runtime.actions.get(identifier)
        return {"action_id":identifier,"state":action.state.value,"version":action.version,
            "decision_id":self.ledger.action_decision(identifier).decision_id,
            "effect_key":action.effect_key,"result":dict(action.result) if action.result is not None else None}

    def case_view(self,case_id):
        history = self.ledger.history(case_id)
        result = {"case":self.ledger.case(case_id),"history":[d.model_dump(mode="json") for d in history],
            "activity":self.ledger.activity(case_id),"tasks":[t for t in self.executor.tasks() if t["decision_id"] in {d.decision_id for d in history}]}
        if history:
            current = history[-1]
            result["snapshot"] = self.ledger.snapshot(current.snapshot_id).model_dump(mode="json")
            result["delta"] = decision_delta(history[0],current,self.ledger.snapshot(history[0].snapshot_id),self.ledger.snapshot(current.snapshot_id))
        runs,actions = self.ledger.links(case_id)
        result["runs"] = [self.run_view(key) for key in runs]
        result["actions"] = [self.action_view(key) for key in actions]
        return result
