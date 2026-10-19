"""Append-only decision history and consumer correlations; AIG owns Action state."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from .contracts import Decision, Snapshot, canonical, sha, utc


class Ledger:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=1)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def provision(self):
        with self.db() as db:
            db.executescript("""
            CREATE TABLE cases(case_id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL, branch TEXT NOT NULL,
                created_utc TEXT NOT NULL, current_decision TEXT);
            CREATE TABLE snapshots(snapshot_id TEXT PRIMARY KEY, digest TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE evidence_records(evidence_id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE decisions(decision_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
                snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), body TEXT NOT NULL);
            CREATE TABLE events(event_id TEXT PRIMARY KEY, case_id TEXT, decision_id TEXT, kind TEXT NOT NULL,
                created_utc TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE acquisitions(acquisition_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
                created_utc TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE runs(run_id TEXT PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES decisions(decision_id));
            CREATE TABLE action_links(action_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id));
            """)
            for table in ("snapshots", "evidence_records", "decisions", "events", "acquisitions", "runs", "action_links"):
                for operation in ("UPDATE", "DELETE"):
                    db.execute(f"CREATE TRIGGER immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable history'); END")

    def new_case(self, scenario_id, branch="original"):
        case_id = str(uuid4())
        with self.db() as db:
            db.execute("INSERT INTO cases VALUES(?,?,?,?,NULL)", (case_id, scenario_id, branch, utc()))
        return case_id

    def case(self, case_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            raise ValueError("case not found")
        return dict(row)

    def cases(self):
        with self.db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM cases ORDER BY created_utc DESC LIMIT 100")]

    def save(self, decision, snapshot):
        if decision.snapshot_id != snapshot.snapshot_id or decision.evidence_digest != snapshot.digest:
            raise ValueError("decision snapshot mismatch")
        with self.db() as db:
            for record in snapshot.records:
                body = canonical(record)
                old = db.execute("SELECT body FROM evidence_records WHERE evidence_id=?",(record.evidence_id,)).fetchone()
                if old is not None and old[0] != body:
                    raise ValueError("evidence identity reused with different content")
                db.execute("INSERT OR IGNORE INTO evidence_records VALUES(?,?)",(record.evidence_id,body))
            db.execute("INSERT OR IGNORE INTO snapshots VALUES(?,?,?)", (snapshot.snapshot_id, snapshot.digest, canonical(snapshot)))
            db.execute("INSERT INTO decisions VALUES(?,?,?,?)", (decision.decision_id,decision.case_id,snapshot.snapshot_id,canonical(decision)))
            db.execute("UPDATE cases SET current_decision=? WHERE case_id=?", (decision.decision_id,decision.case_id))

    def decision(self, decision_id):
        with self.db() as db:
            row = db.execute("SELECT body FROM decisions WHERE decision_id=?", (decision_id,)).fetchone()
        if row is None:
            raise ValueError("decision not found")
        return Decision.model_validate_json(row[0])

    def snapshot(self, snapshot_id):
        with self.db() as db:
            row = db.execute("SELECT body FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if row is None:
            raise ValueError("snapshot not found")
        value = Snapshot.model_validate_json(row[0])
        if Snapshot.build(value.records,value.as_of).digest != value.digest:
            raise ValueError("evidence digest mismatch")
        return value

    def history(self, case_id):
        with self.db() as db:
            return [Decision.model_validate_json(row[0]) for row in db.execute("SELECT body FROM decisions WHERE case_id=? ORDER BY rowid", (case_id,))]

    def event(self, case_id, kind, body, decision_id=None):
        with self.db() as db:
            db.execute("INSERT INTO events VALUES(?,?,?,?,?,?)", (str(uuid4()),case_id,decision_id,kind,utc(),canonical(body)))

    def acquisition(self, case_id, body):
        with self.db() as db:
            db.execute("INSERT INTO acquisitions VALUES(?,?,?,?)", (str(uuid4()),case_id,utc(),canonical(body)))

    def activity(self, case_id):
        with self.db() as db:
            return {"events":[dict(r) | {"body":json.loads(r["body"])} for r in db.execute("SELECT * FROM events WHERE case_id=? ORDER BY rowid",(case_id,))],
                    "acquisitions":[dict(r) | {"body":json.loads(r["body"])} for r in db.execute("SELECT * FROM acquisitions WHERE case_id=? ORDER BY rowid",(case_id,))]}

    def link_run(self, run_id, decision_id):
        with self.db() as db:
            db.execute("INSERT INTO runs VALUES(?,?)",(run_id,decision_id))

    def run_decision(self, run_id):
        with self.db() as db:
            row = db.execute("SELECT decision_id FROM runs WHERE run_id=?",(run_id,)).fetchone()
        if row is None:
            raise ValueError("unlinked Run")
        return self.decision(row[0])

    def link_action(self, action_id, run_id):
        with self.db() as db:
            db.execute("INSERT OR IGNORE INTO action_links VALUES(?,?)",(action_id,run_id))

    def action_decision(self, action_id):
        with self.db() as db:
            row = db.execute("SELECT run_id FROM action_links WHERE action_id=?",(action_id,)).fetchone()
        if row is None:
            raise ValueError("unlinked Action")
        return self.run_decision(row[0])

    def links(self, case_id):
        with self.db() as db:
            runs = [r[0] for r in db.execute("SELECT r.run_id FROM runs r JOIN decisions d ON d.decision_id=r.decision_id WHERE d.case_id=?",(case_id,))]
            actions = [r[0] for r in db.execute("SELECT a.action_id FROM action_links a JOIN runs r ON r.run_id=a.run_id JOIN decisions d ON d.decision_id=r.decision_id WHERE d.case_id=?",(case_id,))]
        return runs, actions

    def denied(self, decision_id):
        with self.db() as db:
            return db.execute("SELECT count(*) FROM events WHERE decision_id=? AND kind='AUTHORIZATION_DENIED'",(decision_id,)).fetchone()[0] > 0


def decision_delta(previous, current, old_snapshot, new_snapshot):
    old = {r.evidence_id:r for r in old_snapshot.active()}
    new = {r.evidence_id:r for r in new_snapshot.active()}
    new_ids = sorted(set(new)-set(old))
    removed_ids = sorted(set(old)-set(new))
    old_fields = {}
    for record in old.values():
        key = (record.asset_id,record.key)
        old_fields.setdefault(key,[])
        if record.value not in old_fields[key]:
            old_fields[key].append(record.value)
    old_fields = {key:values[0] if len(values)==1 else values for key,values in old_fields.items()}
    changes = [{"asset_id":r.asset_id,"field":r.key,"before":old_fields.get((r.asset_id,r.key)),"after":r.value,"evidence_id":r.evidence_id}
               for identifier,r in new.items() if identifier in new_ids and old_fields.get((r.asset_id,r.key)) != r.value]
    before = [r.asset_id for r in previous.ranking]
    after = [r.asset_id for r in current.ranking]
    explanation = ("Ranking changed" if before != after else "Ranking unchanged") + "; "
    explanation += ", ".join(f"{c['asset_id']} {c['field']}: {c['before']} → {c['after']}" for c in changes) or "no changed facts"
    return {"previous_decision_id":previous.decision_id,"current_decision_id":current.decision_id,
        "previous_evidence_digest":old_snapshot.digest,"current_evidence_digest":new_snapshot.digest,
        "new_evidence_ids":new_ids,"removed_or_superseded_claims":removed_ids,"previous_ranking":before,"current_ranking":after,
        "changed_assumptions":{"removed":sorted(set(previous.assumptions)-set(current.assumptions)),"added":sorted(set(current.assumptions)-set(previous.assumptions))},
        "changed_fields":changes,"remaining_uncertainties":list(current.uncertainties),"explanation":explanation,
        "ranking_changed":before != after,"selection_changed":previous.selected_asset != current.selected_asset}
