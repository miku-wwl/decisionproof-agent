"""Human-specified synthetic scenario expectations, authored before the engine."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

AS_OF = "2026-10-20T00:00:00Z"


def asset(identifier, severity=8, criticality=3, exposed=True, **changes):
    value = dict(id=identifier, name={"A": "Branch gateway", "B": "Customer portal"}[identifier],
                 kev_product="ExampleOS", product="ExampleOS", severity=severity, version="3.1",
                 exposed=exposed, criticality=criticality, maintenance="Reviewed window available", observed_utc=AS_OF)
    return value | changes


def specifications():
    cases = []
    def add(identifier, title, category, assets, selection, followups=None, execution="success", delta="unchanged"):
        cases.append(dict(id=identifier, title=title, category=category, as_of=AS_OF, synthetic=True,
            assets=assets, followups=followups or {}, expected=dict(selection=selection,
            terminal="ABSTAIN" if selection is None else "READY_FOR_HUMAN_REVIEW", delta=delta, execution=execution),
            expectation_note=title + "; expectation authored separately before evaluated engine implementation."))
    add("s01", "Clear exposed business-critical priority", "clear", [asset("A",9,4),asset("B",7,2)], "A")
    add("s02", "Severity alone misses exposed customer service", "misleading severity", [asset("A",10,1,False),asset("B",7,4)], "B")
    add("s03", "Vendor-only KEV match is irrelevant", "irrelevant product", [asset("A",10,5,product="DifferentOS"),asset("B",7,3)], "B")
    add("s04", "Missing version requires permitted inventory read", "missing version", [asset("A",9,4,version=None)], "A", {"asset_details:A":[{"version":"3.1"}]})
    add("s05", "Fresh observation supersedes conflicting exposure", "conflict", [asset("A",9,4,exposed=[True,False]),asset("B",8,3)], "B", {"asset_details:A":[{"exposed":False}]}, delta="changed")
    add("s06", "Stale inventory needs a fresh bounded read", "stale inventory", [asset("A",9,4,observed_utc="2026-08-01T00:00:00Z")], "A", {"asset_details:A":[{"product":"ExampleOS","version":"3.1","exposed":True,"criticality":4}]})
    add("s07", "Criticality update changes the maintenance choice", "changed criticality", [asset("A",9,4,maintenance=None),asset("B",8,None)], "B", {"asset_details:B":[{"criticality":5}],"maintenance_context:A":[{"maintenance":"Reviewed window available"}]}, delta="changed")
    add("s08", "Missing maintenance context requires abstention", "missing policy", [asset("A",9,4,maintenance=None)], None)
    add("s09", "Hero: missing exposure reveals a stronger priority", "decision revision", [asset("A",9,3),asset("B",8,2,exposed=None)], "B", {"asset_details:B":[{"exposed":True,"criticality":5}]}, delta="changed")
    add("s10", "Additional evidence confirms the existing choice", "no reversal", [asset("A",9,4,maintenance=None),asset("B",7,2)], "A", {"maintenance_context:A":[{"maintenance":"Reviewed window available"}]})
    add("s11", "No relevant product requires abstention", "necessary abstention", [asset("A",10,5,product="Unrelated")], None)
    add("s12", "Denied authorization creates no task", "authorization denied", [asset("A",9,4)], "A", execution="deny")
    add("s13", "Lost acknowledgment stays Unknown after one task", "ambiguous effect", [asset("A",9,4)], "A", execution="unknown")
    add("s14", "Pre-dispatch rejection produces Failed without a task", "failed effect", [asset("A",9,4)], "A", execution="fail")
    add("s15", "Two insufficient reads require abstention", "unresolved evidence", [asset("A",9,4,version=None)], None, {"asset_details:A":[{},{}]})
    add("s16", "Critical internal system outranks minor exposed service", "baseline counterexample", [asset("A",8,5,False),asset("B",8,1,True)], "A")
    return cases


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    path = root / "fixtures/scenarios.json"
    if path.exists():
        raise SystemExit("Specification already exists; do not overwrite frozen expectations")
    path.parent.mkdir(exist_ok=True)
    data = (json.dumps({"description":"Entirely synthetic, including KEV-like records. No real CISA observations.",
                       "scenarios":specifications()},indent=2)+"\n").encode()
    path.write_bytes(data)
    evidence = root / "docs/evidence/p1a"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "scenario-specification.json").write_text(json.dumps({"authored_before_engine":True,
        "authorship":"Same implementer; independently specified expected outcomes, not blinded external validation",
        "utc":datetime.now(timezone.utc).isoformat(),"count":16,"sha256":hashlib.sha256(data).hexdigest(),
        "expected_outcomes":{s["id"]:s["expected"] for s in specifications()}},indent=2)+"\n",encoding="utf-8")
    print("Frozen 16 scenarios and expected outcomes before engine implementation")
