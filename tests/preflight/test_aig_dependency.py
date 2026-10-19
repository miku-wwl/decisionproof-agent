"""P0-only installed-dependency qualification; no competition product code.

Read the original pinned example from uv's external cache. Never copy core source
or add the checkout to sys.path. All effects are synthetic local SQLite writes.
"""
import asyncio
import base64
import csv
import hashlib
import importlib.metadata
import inspect
import io
import json
import os
from pathlib import Path
import runpy
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest
import agentic_intent_gate.runtime as api

PIN = "7261fdd2f47d2b15fabe8faac527eeee37338eb1"
ROOT = Path(__file__).resolve().parents[2]
REPORT = {"kind": "synthetic dependency smoke; scripted example consent", "checks": {}}


def count_entries(directory):
    with sqlite3.connect(f"file:{(directory / 'effects.sqlite3').as_posix()}?mode=ro", uri=True) as db:
        return db.execute("SELECT count(*) FROM entries").fetchone()[0]


def durable_summary(directory):
    with sqlite3.connect(f"file:{(directory / 'gate.sqlite3').as_posix()}?mode=ro", uri=True) as db:
        return {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("action_attempts", "action_events")}


@pytest.fixture(scope="session")
def reference():
    checkout = Path(os.environ["P0_AIG_REFERENCE"]).resolve()
    sha = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    assert sha == PIN
    example = checkout / "examples/consumer/app.py"
    REPORT["example_sha256"] = hashlib.sha256(example.read_bytes()).hexdigest()
    original = runpy.run_path(str(example))
    yield original, example
    (ROOT / "docs/evidence").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/evidence/aig-smoke.json").write_text(json.dumps(REPORT, indent=2) + "\n", encoding="utf-8")


def provision(reference):
    original, _ = reference
    directory = ROOT / ".preflight/private" / str(uuid4())
    original["provision"](directory)
    return original, directory


def bearer(directory):
    return "Bearer " + (directory / "capability").read_text("ascii")


def restart_read(reference, directory, action_id, expected):
    # Actual separate Python process; read durable state, never dispatch on recovery.
    _, example = reference
    program = """
import json,runpy,sys
from pathlib import Path
app=runpy.run_path(sys.argv[1])
with app['consumer'](Path(sys.argv[2]),predecessor_stopped=True) as (runtime,_):
    action=runtime.actions.get(sys.argv[3])
    print(json.dumps({'state':action.state.value}))
"""
    result = subprocess.run([sys.executable, "-I", "-c", program, str(example), str(directory), action_id],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["state"] == expected


def test_pinned_installed_distribution(reference):
    distribution = importlib.metadata.distribution("agentic-intent-gate")
    direct = json.loads(distribution.read_text("direct_url.json"))
    assert distribution.version == "0.2.0"
    assert direct["vcs_info"]["commit_id"] == PIN
    assert Path(api.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    assert "site-packages" in Path(api.__file__).parts
    assert inspect.signature(api.open_runtime).parameters["execution_timeout_seconds"].default == 5
    verified = []
    for name, encoded, size in csv.reader(io.StringIO(distribution.read_text("RECORD"))):
        if not encoded:
            continue
        algorithm, expected = encoded.split("=", 1)
        actual = base64.urlsafe_b64encode(hashlib.new(algorithm, distribution.locate_file(name).read_bytes()).digest()).decode().rstrip("=")
        assert actual == expected, name
        verified.append(name)
    (ROOT / "docs/evidence/installed-record.json").write_text(json.dumps({"status": "PASS",
        "distribution": distribution.version, "record_hashes_verified": len(verified), "files": verified}, indent=2) + "\n", encoding="utf-8")
    names = ("ToolBinding", "ToolCapability", "ExecutableRegistry", "CapabilityVerifier",
             "BoundCapabilityAuthorization", "execution_budget_binding", "open_runtime",
             "Intent", "ModelProvider", "ToolExecutor", "ApprovalDecisionRequest",
             "AdmissionCommand", "ActionCommand", "ToolOutcome")
    REPORT["checks"]["installed_identity"] = {"status": "PASS", "version": distribution.version,
        "source": direct, "module_relative_to_venv": str(Path(api.__file__).relative_to(sys.prefix)),
        "signatures": {name: str(inspect.signature(getattr(api, name))) for name in names}}
    REPORT["checks"]["installed_identity"]["record_hashes_verified"] = len(verified)
    REPORT["checks"]["installed_identity"]["signatures"].update({
        "ModelProvider.generate_plan": str(inspect.signature(api.ModelProvider.generate_plan)),
        "ToolExecutor.execute": str(inspect.signature(api.ToolExecutor.execute)),
    })


def test_success_replay_receipt_and_process_restart(reference):
    original, directory = provision(reference)
    with original["consumer"](directory, predecessor_stopped=True) as (runtime, _):
        action = asyncio.run(original["workflow"](runtime, bearer(directory)))
        assert action.state.value == "Succeeded"
        assert runtime.actions.get(action.action_id) == action
        with sqlite3.connect(directory / "effects.sqlite3") as db:
            rows = db.execute("SELECT effect_key,payload_digest,receipt FROM entries").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == action.effect_key
        assert rows[0][2] == action.result["receipt_reference"]
        summary = durable_summary(directory)
        assert summary == {"action_attempts": 1, "action_events": 4}
        REPORT["public_methods"] = {name: str(inspect.signature(getattr(obj, method))) for name, obj, method in (
            ("run_service.create",runtime.run_service,"create"), ("run_service.decide",runtime.run_service,"decide"),
            ("actions.get",runtime.actions,"get"), ("gateway.admit",runtime.gateway,"admit"),
            ("gateway.authorize",runtime.gateway,"authorize"), ("gateway.execute",runtime.gateway,"execute"))}
    restart_read(reference, directory, action.action_id, "Succeeded")
    assert count_entries(directory) == 1
    REPORT["checks"]["success"] = {"status": "PASS", "state": "Succeeded", "effects": 1,
        "exact_command_replay": True, "new_process_read": "Succeeded", "receipt_correlated": True, **summary}


def test_approval_without_authorization_never_dispatches(reference):
    original, directory = provision(reference)
    async def scenario(runtime):
        principal = runtime.verifier.verify(bearer(directory))
        run = await runtime.run_service.create(api.Intent("Append a reviewed audit entry"))
        approved = runtime.run_service.decide(run.run_id, api.ApprovalDecisionRequest(api.ApprovalChoice.APPROVE, run.version))
        action = runtime.gateway.admit(api.AdmissionCommand(approved.run_id, approved.version, principal.subject_id, str(uuid4())), principal).action
        with pytest.raises(Exception) as caught:
            await runtime.gateway.execute(api.ActionCommand(action.action_id, action.version, str(uuid4())), principal)
        assert str(getattr(caught.value, "code", None)) == "ACTION_NOT_EXECUTABLE"
        assert count_entries(directory) == 0
        return str(caught.value.code)
    with original["consumer"](directory, predecessor_stopped=True) as (runtime, _):
        code = asyncio.run(scenario(runtime))
    REPORT["checks"]["missing_authorization"] = {"status": "PASS", "error_code": code, "effects": 0}


def test_lost_ack_is_unknown_without_second_effect(reference):
    original, directory = provision(reference)
    with original["consumer"](directory, predecessor_stopped=True, lose_ack=True) as (runtime, _):
        action = asyncio.run(original["workflow"](runtime, bearer(directory)))
        assert action.state.value == "Unknown"
        assert count_entries(directory) == 1
        assert durable_summary(directory)["action_attempts"] == 1
    restart_read(reference, directory, action.action_id, "Unknown")
    assert count_entries(directory) == 1
    REPORT["checks"]["lost_ack"] = {"status": "PASS", "state": "Unknown", "effects": 1,
        "exact_command_replay": True, "new_process_read": "Unknown", "attempts": 1}


def test_unregistered_tool_plan_has_no_approvable_run(reference):
    original, directory = provision(reference)
    raw = json.loads(original["DeterministicProvider"]().raw)
    raw["steps"][0]["tool_name"] = "unregistered_tool"
    provider = original["DeterministicProvider"](raw=json.dumps(raw))
    with original["consumer"](directory, predecessor_stopped=True, provider=provider) as (runtime, _):
        run = asyncio.run(runtime.run_service.create(api.Intent("Append a reviewed audit entry")))
        assert run.state.value != "AwaitingApproval"
        assert count_entries(directory) == 0
        assert runtime.runs.get(run.run_id).state == run.state
    REPORT["checks"]["unknown_tool"] = {"status": "PASS", "run_state": run.state.value, "effects": 0}
