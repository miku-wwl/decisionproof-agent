import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from agentic_intent_gate.runtime import ExecutableRegistry,ExecutionSpec

from decisionproof.contracts import Candidate,EvidenceBatch,RetrievalIntent,canonical
from decisionproof.ledger import Ledger,decision_delta
from decisionproof.reasoning import ReasoningLoop,validate_decision
from decisionproof.service import consumer,provision
from decisionproof.sources import OfflineSource,scenario,scenarios
from decisionproof.web import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def private(tmp_path):
    path = tmp_path/"sandbox"
    provision(path,"fixture-only-password-123")
    return path


async def ready(service,identifier="s09"):
    data = await service.analyze(identifier)
    decision = data["history"][-1]
    plan = await service.propose(decision["decision_id"])
    plan = service.approve(plan["run_id"],plan["version"],plan["review_fingerprint"])
    action = service.admit(plan["run_id"],plan["version"],str(uuid4()))
    return data,plan,action


@pytest.mark.parametrize("identifier",[s["id"] for s in scenarios()])
def test_separately_specified_scenarios(private,identifier):
    async def check():
        with consumer(private,predecessor_stopped=True) as service:
            data = await service.analyze(identifier)
            last = data["history"][-1]
            expected = scenario(identifier)["expected"]
            assert last["selected_asset"] == expected["selection"]
            assert last["state"] == expected["terminal"]
            assert last["rounds"] <= 2
            assert validate_decision(service.ledger.decision(last["decision_id"]),service.ledger.snapshot(last["snapshot_id"]))
            if expected["selection"] is None:
                with pytest.raises(ValueError):
                    await service.propose(last["decision_id"])
            assert not service.executor.tasks()
    asyncio.run(check())


def test_delta_and_append_only_history_after_restart(private):
    with consumer(private,predecessor_stopped=True) as service:
        data = asyncio.run(service.analyze("s09"))
        assert data["delta"]["previous_ranking"] == ["A","B"]
        assert data["delta"]["current_ranking"] == ["B","A"]
        assert {(x["field"],x["after"]) for x in data["delta"]["changed_fields"]} == {("exposed",True),("criticality",5)}
        assert data["delta"]["previous_evidence_digest"] != data["delta"]["current_evidence_digest"]
        assert data["delta"]["removed_or_superseded_claims"]
        with service.ledger.db() as db:
            with pytest.raises(sqlite3.IntegrityError,match="immutable"):
                db.execute("UPDATE decisions SET body='{}'")
    # New runtime and independently opened decision store, no in-memory history reuse.
    with consumer(private,predecessor_stopped=True) as service:
        again = service.case_view(data["case"]["case_id"])
        assert again["history"] == data["history"]
        assert again["delta"] == data["delta"]


def test_followup_that_does_not_reverse_and_counterfactual_isolation(private):
    with consumer(private,predecessor_stopped=True) as service:
        data = asyncio.run(service.analyze("s10"))
        assert not data["delta"]["ranking_changed"]
        assert data["delta"]["new_evidence_ids"]
        original = canonical(data)
        other = asyncio.run(service.analyze("s10",counterfactual=True))
        assert other["case"]["case_id"] != data["case"]["case_id"]
        assert other["case"]["branch"] == "synthetic counterfactual"
        assert canonical(service.case_view(data["case"]["case_id"])) == original


def test_strict_retrieval_contract_and_overall_deadline(private):
    class Slow(OfflineSource):
        started = False
        cancelled = False
        async def retrieve(self,intent,snapshot):
            self.started = True
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                self.cancelled = True
                raise
            return EvidenceBatch(records=(),provider="test-slow")
    class Escape(OfflineSource):
        async def retrieve(self,intent,snapshot):
            record = next(r for r in snapshot.records if r.asset_id != intent.asset_id)
            return EvidenceBatch(records=(record,),provider="test-escape")
    with consumer(private,predecessor_stopped=True) as service:
        for source,deadline in [(Slow(scenario("s09")),0.1),(Escape(scenario("s09")),3)]:
            case = service.ledger.new_case("s09")
            d = asyncio.run(ReasoningLoop(service.ledger,source,deadline_seconds=deadline).run(case))
            assert d.state == "ABSTAIN"
            acquisitions = service.ledger.activity(case)["acquisitions"]
            if isinstance(source,Slow):
                assert (d.rounds==0 and not acquisitions and not source.started) or (d.rounds==1 and source.cancelled and acquisitions[0]["body"]["status"]=="REFUSED")
                (ROOT/'docs/evidence/p1a/deadline-case.json').write_text(json.dumps({"status":"PASS","rounds":d.rounds,
                    "read_started":source.started,"read_cancelled":source.cancelled,"terminal":d.state,"task_rows":len(service.executor.tasks())},indent=2)+'\n',encoding='utf-8')
            else:
                assert d.rounds == 1 and acquisitions[0]["body"]["status"] == "REFUSED"
            assert not service.executor.tasks()


def test_independent_validator_rejects_planner_claims(private):
    class Invented:
        def propose(self,snapshot):
            return (Candidate(asset_id="A",cve_id="CVE-2099-0001",score=99,evidence_ids=("invented",),explanation="Unsupported"),)
    with consumer(private,predecessor_stopped=True) as service:
        case = service.ledger.new_case("s01")
        d = asyncio.run(ReasoningLoop(service.ledger,OfflineSource(scenario("s01")),planner=Invented()).run(case))
        assert d.state == "ABSTAIN" and d.selected_asset is None
        assert not service.executor.tasks()


def test_real_aig_success_missing_authorization_and_exact_replay(private):
    async def check():
        with consumer(private,predecessor_stopped=True) as service:
            data,plan,action = await ready(service)
            with pytest.raises(Exception) as missing:
                await service.execute(action["action_id"],action["version"],str(uuid4()))
            assert str(missing.value.code) == "ACTION_NOT_EXECUTABLE"
            assert not service.executor.tasks()
            action = service.authorize(action["action_id"],action["version"],str(uuid4()))
            version,key = action["version"],str(uuid4())
            result = await service.execute(action["action_id"],version,key)
            replay = await service.execute(action["action_id"],version,key)
            assert result["state"] == "Succeeded" and replay["replayed"]
            assert len(service.executor.tasks()) == 1
            assert service.executor.tasks()[0]["receipt"] == result["result"]["receipt_reference"]
    asyncio.run(check())


def test_separate_denial_blocks_dispatch_and_cannot_be_reused(private):
    async def check():
        with consumer(private,predecessor_stopped=True) as service:
            _,_,action = await ready(service)
            service.authorize(action["action_id"],1,str(uuid4()),False)
            with pytest.raises(ValueError,match="denied"):
                await service.execute(action["action_id"],1,str(uuid4()))
            with pytest.raises(ValueError,match="denied"):
                service.authorize(action["action_id"],1,str(uuid4()),True)
            assert not service.executor.tasks()
    asyncio.run(check())


def test_changed_evidence_or_decision_needs_fresh_approval_and_authorization(private):
    async def check():
        with consumer(private,predecessor_stopped=True) as service:
            data,plan,action = await ready(service)
            old_plan = service.run_view(plan["run_id"])["plan"]
            await service.analyze("s09",case_id=data["case"]["case_id"])
            assert service.run_view(plan["run_id"])["plan"] == old_plan
            with pytest.raises(ValueError,match="fresh Plan"):
                service.authorize(action["action_id"],1,str(uuid4()))
            with pytest.raises(ValueError,match="fresh Plan"):
                await service.execute(action["action_id"],1,str(uuid4()))
            assert not service.executor.tasks()
    asyncio.run(check())


@pytest.mark.parametrize("field",["tool_name","target","binding_revision","execution_scope"])
def test_public_registry_denies_wrong_identity(private,field):
    async def check():
        with consumer(private,predecessor_stopped=True) as service:
            _,_,action = await ready(service)
            original = service.runtime.actions.get(action["action_id"])
            spec = ExecutionSpec.from_compiled(original.spec)
            registry = ExecutableRegistry(service.executor,binding=service.executor.binding)
            with pytest.raises(Exception):
                registry.resolve(replace(spec,**{field:str(uuid4()) if field=="execution_scope" else "wrong"}))
            assert not service.executor.tasks()
    asyncio.run(check())


@pytest.mark.parametrize("fault,expected,count",[("fail","Failed",0),("unknown","Unknown",1)])
def test_failed_and_ambiguous_outcomes_are_durable(private,fault,expected,count):
    async def check():
        with consumer(private,predecessor_stopped=True,fault=fault) as service:
            data,_,action = await ready(service)
            action = service.authorize(action["action_id"],1,str(uuid4()))
            key = str(uuid4())
            result = await service.execute(action["action_id"],2,key)
            assert result["state"] == expected
            assert (await service.execute(action["action_id"],2,key))["replayed"]
            assert len(service.executor.tasks())==count
        with consumer(private,predecessor_stopped=True) as service:
            assert service.action_view(action["action_id"])["state"] == expected
            assert len(service.executor.tasks())==count
    asyncio.run(check())


def test_concurrent_and_conflicting_commands_never_duplicate_task(private):
    async def check():
        with consumer(private,predecessor_stopped=True) as service:
            _,_,action = await ready(service)
            action = service.authorize(action["action_id"],1,str(uuid4()))
            key = str(uuid4())
            results = await asyncio.gather(service.execute(action["action_id"],2,key),service.execute(action["action_id"],2,key),return_exceptions=True)
            assert any(isinstance(r,dict) and r["state"]=="Succeeded" for r in results)
            assert len(service.executor.tasks())==1
            with pytest.raises(Exception):
                await service.execute(action["action_id"],2,str(uuid4()))
            assert len(service.executor.tasks())==1
    asyncio.run(check())


def test_actual_process_crash_after_effect_recovers_without_replay(private):
    program = """
import asyncio,json,sys
from pathlib import Path
from uuid import uuid4
from decisionproof.service import consumer
async def run():
    with consumer(Path(sys.argv[1]),predecessor_stopped=True,fault='crash') as s:
        data=await s.analyze('s01');p=await s.propose(data['history'][-1]['decision_id'])
        p=s.approve(p['run_id'],p['version'],p['review_fingerprint'])
        a=s.admit(p['run_id'],p['version'],str(uuid4()));a=s.authorize(a['action_id'],1,str(uuid4()))
        (Path(sys.argv[1])/'crash-action.json').write_text(json.dumps({'action_id':a['action_id']}))
        await s.execute(a['action_id'],2,str(uuid4()))
asyncio.run(run())
"""
    child = subprocess.run([sys.executable,"-c",program,str(private)],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert child.returncode == 91, child.stderr
    identifier = json.loads((private/"crash-action.json").read_text())["action_id"]
    with consumer(private,predecessor_stopped=True) as service:
        assert service.action_view(identifier)["state"] == "Unknown"
        assert len(service.executor.tasks())==1
        with sqlite3.connect(private/"gate.sqlite3") as db:
            assert db.execute("SELECT count(*) FROM action_attempts").fetchone()[0]==1


def test_http_auth_csrf_and_schema_boundaries(private):
    app = create_app(private,origin="http://testserver",predecessor_stopped=True)
    with TestClient(app,raise_server_exceptions=False) as client:
        assert client.get('/api/cases').status_code==401
        assert client.post('/api/analyze',json={"scenario_id":"s01"}).status_code==403
        login = client.post('/api/login',json={"password":"fixture-only-password-123"},headers={"Origin":"http://testserver","X-Requested-With":"DecisionProof"})
        assert login.status_code==200
        assert 'HttpOnly' in login.headers['set-cookie'] and 'SameSite=strict' in login.headers['set-cookie']
        headers={"Origin":"http://testserver","X-CSRF-Token":login.json()['csrf']}
        assert client.post('/api/analyze',json={"scenario_id":"s01"},headers={"Origin":"http://testserver"}).status_code==403
        assert client.post('/api/analyze',json={"scenario_id":"s01","execution_timeout_seconds":15},headers=headers).status_code==422
        result=client.post('/api/analyze',json={"scenario_id":"s01"},headers=headers)
        assert result.status_code==200
        body=canonical(result.json())
        assert (private/'capability').read_text('ascii') not in body
        assert 'Content-Security-Policy' in result.headers
        assert client.get('/api/runs').status_code==404  # No unprotected bundled demo router.


def test_stale_version_and_changed_plan_fingerprint_refused(private):
    async def check():
        with consumer(private,predecessor_stopped=True) as service:
            data=await service.analyze('s01');plan=await service.propose(data['history'][-1]['decision_id'])
            with pytest.raises(ValueError,match='Plan changed'):
                service.approve(plan['run_id'],plan['version'],'0'*64)
            with pytest.raises(Exception):
                service.approve(plan['run_id'],999,plan['review_fingerprint'])
            assert not service.executor.tasks()
    asyncio.run(check())
