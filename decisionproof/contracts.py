"""Provider-neutral, strict evidence/reasoning contracts. No sponsor API assumptions."""
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def canonical(value):
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Provenance(Strict):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: Literal["kev", "advisory", "inventory", "policy"]
    reference: str = Field(min_length=1, max_length=256)
    synthetic: bool
    observed_utc: str
    @field_validator("observed_utc")
    @classmethod
    def valid_time(cls, value):
        parse_time(value)
        return value


Key = Literal["cve_id", "kev_product", "product", "severity", "version", "exposed", "criticality", "maintenance"]


class Evidence(Strict):
    evidence_id: str = Field(min_length=1, max_length=160)
    asset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,32}$")
    key: Key
    value: str | int | bool
    provenance: Provenance
    supersedes: tuple[str, ...] = Field(default=(), max_length=8)


SOURCES = {"cve_id":"kev", "kev_product":"kev", "severity":"advisory", "product":"inventory", "version":"inventory",
           "exposed":"inventory", "criticality":"inventory", "maintenance":"policy"}


def validate_records(records):
    if len(records) > 80 or len(canonical([r.model_dump(mode="json") for r in records]).encode()) > 131072:
        raise ValueError("evidence size limit")
    seen = {}
    for record in records:
        if record.evidence_id in seen:
            raise ValueError("duplicate evidence identity")
        if record.provenance.source_type != SOURCES[record.key]:
            raise ValueError("source cannot assert this field")
        value = record.value
        if record.key == "cve_id":
            valid = type(value) is str and re.fullmatch(r"CVE-[0-9]{4}-[0-9]{4,8}",value) is not None
        elif record.key == "exposed":
            valid = type(value) is bool
        elif record.key in ("severity", "criticality"):
            valid = type(value) is int and 1 <= value <= (10 if record.key == "severity" else 5)
        else:
            valid = type(value) is str and 1 <= len(value) <= 160
        if not valid:
            raise ValueError("invalid typed evidence")
        for old_id in record.supersedes:
            old = seen.get(old_id)
            if old is None or (old.asset_id, old.key) != (record.asset_id, record.key):
                raise ValueError("invalid supersession")
        seen[record.evidence_id] = record
    return records


class Snapshot(Strict):
    snapshot_id: str
    as_of: str
    records: tuple[Evidence, ...]
    digest: str

    @classmethod
    def build(cls, records, as_of):
        parse_time(as_of)
        records = tuple(validate_records(tuple(records)))
        digest = sha({"as_of":as_of, "records":[r.model_dump(mode="json") for r in records]})
        return cls(snapshot_id=str(uuid4()), as_of=as_of, records=records, digest=digest)

    def active(self):
        removed = {key for record in self.records for key in record.supersedes}
        return tuple(r for r in self.records if r.evidence_id not in removed)


class RetrievalIntent(Strict):
    query: Literal["asset_details", "maintenance_context"]
    asset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,32}$")


class EvidenceBatch(Strict):
    records: tuple[Evidence, ...] = Field(max_length=16)
    provider: str = Field(min_length=1, max_length=80)


class ContextSource(Protocol):
    def initial(self) -> Snapshot: ...
    async def retrieve(self, intent: RetrievalIntent, snapshot: Snapshot) -> EvidenceBatch: ...


class Gap(Strict):
    asset_id: str
    field: Key
    kind: Literal["missing", "conflict", "stale"]


class Critique(Strict):
    gaps: tuple[Gap, ...]
    notes: tuple[str, ...]


class Candidate(Strict):
    asset_id: str
    cve_id: str
    score: int
    evidence_ids: tuple[str, ...]
    explanation: str


class Claim(Strict):
    evidence_id: str
    field: Key
    value: str | int | bool


class Decision(Strict):
    decision_id: str
    case_id: str
    previous_decision_id: str | None
    snapshot_id: str
    evidence_digest: str
    created_utc: str
    state: Literal["PROVISIONAL", "READY_FOR_HUMAN_REVIEW", "ABSTAIN"]
    ranking: tuple[Candidate, ...]
    selected_asset: str | None
    critique: Critique
    claims: tuple[Claim, ...]
    assumptions: tuple[str, ...]
    uncertainties: tuple[str, ...]
    rounds: int = Field(ge=0, le=2)
    summary: str
    provider: Literal["offline-deterministic"] = "offline-deterministic"


class Planner(Protocol):
    def propose(self, snapshot: Snapshot) -> tuple[Candidate, ...]: ...


class RetrievalPlanner(Protocol):
    def select(self, critique: Critique, snapshot: Snapshot) -> RetrievalIntent | None: ...


def validate_batch(intent, batch, snapshot):
    if not isinstance(batch, EvidenceBatch):
        raise ValueError("normalized EvidenceBatch required")
    allowed = {"maintenance"} if intent.query == "maintenance_context" else {"product","version","exposed","criticality"}
    if len(canonical(batch).encode()) > 32768:
        raise ValueError("batch byte limit")
    for record in batch.records:
        if record.asset_id != intent.asset_id or record.key not in allowed:
            raise ValueError("retrieval escaped permitted intention")
    validate_records(snapshot.records + batch.records)


class LiveIntegrationUnavailable:
    """An explicit blocker, not an invented Zetaris/Nemotron implementation."""
    async def retrieve(self, intent, snapshot):
        raise RuntimeError("Live sponsor integration BLOCKED; assigned contract and verification required")
