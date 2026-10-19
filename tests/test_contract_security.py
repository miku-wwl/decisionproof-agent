import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from decisionproof.contracts import EvidenceBatch,RetrievalIntent,Snapshot,validate_batch
from decisionproof.reasoning import ReasoningLoop
from decisionproof.reasoning import validate_decision
from decisionproof.service import consumer,provision
from decisionproof.sources import OfflineSource,scenario
from decisionproof.web import create_app


def test_query_and_result_schemas_are_bounded_not_sql_or_code():
    for query in ('SELECT * FROM secrets','http://example.com','shell'):
        with pytest.raises(ValidationError):
            RetrievalIntent(query=query,asset_id='A')
    with pytest.raises(ValidationError):
        RetrievalIntent(query='asset_details',asset_id='A',sql='DROP TABLE inventory')
    source=OfflineSource(scenario('s09'));snapshot=source.initial()
    with pytest.raises(ValidationError):
        EvidenceBatch(records=snapshot.records*3,provider='oversized')
    wrong=EvidenceBatch(records=(snapshot.records[0],),provider='invalid-field')
    with pytest.raises(ValueError,match='escaped'):
        validate_batch(RetrievalIntent(query='maintenance_context',asset_id='A'),wrong,snapshot)


def test_conflicting_receipt_identity_fails_without_task(tmp_path):
    path=tmp_path/'sandbox';provision(path,'fixture-only-password-123')
    async def run():
        with consumer(path,predecessor_stopped=True) as s:
            d=(await s.analyze('s01'))['history'][-1]
            p=await s.propose(d['decision_id']);p=s.approve(p['run_id'],p['version'],p['review_fingerprint'])
            a=s.admit(p['run_id'],p['version'],str(uuid4()));s.authorize(a['action_id'],1,str(uuid4()))
            # Alter only this fresh test-owned consumer receipt store, not the shared Runtime.
            import sqlite3
            with sqlite3.connect(path/'tasks.sqlite3') as db:
                db.execute("UPDATE identity SET binding='wrong-profile'")
            result=await s.execute(a['action_id'],2,str(uuid4()))
            assert result['state']=='Failed' and not s.executor.tasks()
    asyncio.run(run())


def test_login_rate_limit_and_no_sensitive_validation_echo(tmp_path):
    path=tmp_path/'sandbox';provision(path,'fixture-only-password-123')
    with TestClient(create_app(path,origin='http://testserver',predecessor_stopped=True)) as c:
        headers={'Origin':'http://testserver','X-Requested-With':'DecisionProof'}
        secret='x'*257
        response=c.post('/api/login',json={'password':secret},headers=headers)
        assert response.status_code==422 and secret not in response.text
        for _ in range(5):
            assert c.post('/api/login',json={'password':'wrong'},headers=headers).status_code==401
        assert c.post('/api/login',json={'password':'fixture-only-password-123'},headers=headers).status_code==429


def test_model_schema_rejection_becomes_abstention(tmp_path):
    path=tmp_path/'sandbox';provision(path,'fixture-only-password-123')
    class InvalidPlanner:
        def propose(self,snapshot):return {'execute':'shell'}
    with consumer(path,predecessor_stopped=True) as s:
        case=s.ledger.new_case('s01')
        d=asyncio.run(ReasoningLoop(s.ledger,OfflineSource(scenario('s01')),planner=InvalidPlanner()).run(case))
        assert d.state=='ABSTAIN' and not d.ranking and not s.executor.tasks()


def test_future_model_intention_is_independently_confined(tmp_path):
    path=tmp_path/'sandbox';provision(path,'fixture-only-password-123')
    class Unrelated:
        def select(self,critique,snapshot):return RetrievalIntent(query='asset_details',asset_id='NOT_IN_CASE')
    with consumer(path,predecessor_stopped=True) as s:
        case=s.ledger.new_case('s09')
        d=asyncio.run(ReasoningLoop(s.ledger,OfflineSource(scenario('s09')),retrieval_planner=Unrelated()).run(case))
        assert d.state=='ABSTAIN' and d.rounds==0
        assert not s.ledger.activity(case)['acquisitions'] and not s.executor.tasks()


def test_delta_preserves_conflict_rather_than_silently_choosing_old_fact(tmp_path):
    path=tmp_path/'sandbox';provision(path,'fixture-only-password-123')
    with consumer(path,predecessor_stopped=True) as s:
        data=asyncio.run(s.analyze('s05'))
        exposure=next(c for c in data['delta']['changed_fields'] if c['field']=='exposed')
        assert exposure['before']==[True,False] and exposure['after'] is False
        assert not data['delta']['ranking_changed']


def test_cve_and_global_evidence_identity_cannot_be_rewritten(tmp_path):
    path=tmp_path/'sandbox';provision(path,'fixture-only-password-123')
    with consumer(path,predecessor_stopped=True) as s:
        data=asyncio.run(s.analyze('s01'))
        d=s.ledger.decision(data['history'][-1]['decision_id']);snap=s.ledger.snapshot(d.snapshot_id)
        forged=d.model_copy(update={'ranking':(d.ranking[0].model_copy(update={'cve_id':'CVE-2099-9999'}),)})
        with pytest.raises(ValueError,match='CVE'):
            validate_decision(forged,snap)
        record=next(r for r in snap.records if r.key=='severity')
        changed=record.model_copy(update={'value':1})
        new=Snapshot.build(tuple(changed if r.evidence_id==record.evidence_id else r for r in snap.records),snap.as_of)
        forged=d.model_copy(update={'decision_id':str(uuid4()),'snapshot_id':new.snapshot_id,'evidence_digest':new.digest})
        with pytest.raises(ValueError,match='identity reused'):
            s.ledger.save(forged,new)
