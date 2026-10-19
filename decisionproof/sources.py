"""Deterministic offline source: reads fixtures, never a sponsor or network API."""
import copy
import json
from pathlib import Path

from .contracts import Evidence, EvidenceBatch, Provenance, SOURCES, Snapshot, sha

SCENARIOS = Path(__file__).resolve().parents[1] / "fixtures/scenarios.json"


def scenarios():
    return json.loads(SCENARIOS.read_text("utf-8"))["scenarios"]


def scenario(identifier):
    found = next((s for s in scenarios() if s["id"] == identifier), None)
    if found is None:
        raise ValueError("unknown fixture scenario")
    return copy.deepcopy(found)


class OfflineSource:
    def __init__(self, specification, *, counterfactual=False):
        # Expected outcomes are deliberately not accessible to planner/source.
        self.assets = copy.deepcopy(specification["assets"])
        self.spec_id = specification["id"]
        self.followups = copy.deepcopy(specification["followups"])
        self.as_of = specification["as_of"]
        self.label = "synthetic-counterfactual" if counterfactual else "synthetic-fixture"
        self.positions = {}
        if counterfactual:
            # One explicitly labeled, isolated hypothetical; never edits original records.
            self.assets[0]["exposed"] = False

    def record(self, asset, key, value, index, observed, supersedes=()):
        prefix = f"{self.label}:{self.spec_id}:{asset}:{key}:{index}"
        identity = sha({"scenario":self.spec_id,"asset":asset,"key":key,"value":value,"index":index,"observed":observed,"supersedes":list(supersedes),"label":self.label})[:12]
        return Evidence(evidence_id=prefix+":"+identity, asset_id=asset,key=key,value=value,
            provenance=Provenance(source_id=f"{self.label}-{self.spec_id}-{SOURCES[key]}",source_type=SOURCES[key],
                reference=f"fixture://{self.label}/{self.spec_id}/{asset}/{key}/{index}",synthetic=True,observed_utc=observed),supersedes=tuple(supersedes))

    def initial(self):
        records = []
        for asset in self.assets:
            for key in SOURCES:
                value = asset.get(key,"CVE-2099-0001" if key=="cve_id" else None)
                if value is not None:
                    values = value if isinstance(value,list) else [value]
                    for index,item in enumerate(values):
                        observed = asset["observed_utc"] if SOURCES[key] == "inventory" else self.as_of
                        records.append(self.record(asset["id"],key,item,f"initial-{index}",observed))
        return Snapshot.build(records,self.as_of)

    async def retrieve(self, intent, snapshot):
        key = intent.query + ":" + intent.asset_id
        index = self.positions.get(key,0)
        self.positions[key] = index + 1
        batches = self.followups.get(key,[])
        values = batches[index] if index < len(batches) else {}
        records = []
        for field,value in values.items():
            old = [r.evidence_id for r in snapshot.active() if r.asset_id == intent.asset_id and r.key == field]
            records.append(self.record(intent.asset_id,field,value,f"query-{index}",self.as_of,old))
        return EvidenceBatch(records=tuple(records),provider="offline-fixture-read")
