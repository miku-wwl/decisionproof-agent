"""Read public documentation/catalogs only; no credentials or inference requests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "event": "https://hackathon.genai.works/event/open-agent-hackathon-2026",
    "academy": "https://academy.genai.works/courses/open-agent-hackathon-2026/details",
    "zetaris_rest": "https://kbase.zetaris.com/knowledge/rest-api",
    "zetaris_docker": "https://kbase.zetaris.com/knowledge/docker-installation-on-docker-desktop",
    "meterless_contract": "https://raw.githubusercontent.com/Meterless/Meterless/main/docs/agent-ready/add-meterless-provider.md",
    "nvidia_catalog": "https://integrate.api.nvidia.com/v1/models",
    "nvidia_inference_docs": "https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-30b-a3b-infer",
    "cisa_kev": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
    "mpi_recalls": "https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/recalled-food-products",
    "meterless_local_catalog": "http://127.0.0.1:8088/v1/models",
    "aig_main_handoff": "https://raw.githubusercontent.com/miku-wwl/agentic-intent-gate/main/docs/V0.2.0-CONSUMER-HANDOFF.md",
}


def retrieve(item):
    name, url = item
    result = {"id": name, "url": url, "method": "unauthenticated GET; TLS verification enabled for HTTPS",
              "observed_utc": datetime.now(timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            body = response.read(8_000_001)
            result.update(http_status=response.status, bytes_read=len(body),
                          sha256=hashlib.sha256(body).hexdigest(),
                          content_type=response.headers.get("Content-Type"))
        if len(body) > 8_000_000:
            result.update(status="PARTIAL", reason="bounded response truncated")
            return result
        text = body.decode("utf-8", errors="replace")
        if "_Incapsula_Resource" in text or "Request unsuccessful" in text:
            result.update(status="BLOCKED", reason="HTTP response is an access-challenge page, not source data")
            return result
        result["status"] = "PASS"
        if name in ("event", "academy"):
            # Public server-rendered React payload, not a private/authenticated API.
            chunks = []
            for match in re.finditer(r'self\.__next_f\.push\((\[.*?\])\)</script>', text):
                try:
                    value = json.loads(match.group(1))
                except ValueError:
                    continue
                if len(value) > 1 and isinstance(value[1], str):
                    chunks.append(value[1])
            decoded = "\n".join(chunks)
            if name == "event":
                start = decoded.find('[{"number":1,"title":"Eligibility"')
                if start < 0:
                    raise ValueError("Official rules array missing; inspect public page again")
                sections, _ = json.JSONDecoder().raw_decode(decoded[start:])
                result["rules_sections"] = [{"number": section["number"], "title": section["title"],
                    "sha256": hashlib.sha256(json.dumps(section, sort_keys=True).encode()).hexdigest()}
                    for section in sections]
                result["rules_section_count"] = len(sections)
                result["required_stack_clause_found"] = "Every submission must integrate Zetaris and Meterless, and teams must use Cursor" in decoded
                result["open_source_permission_found"] = "Pre-existing open-source libraries are fine" in decoded
            else:
                result["direct_nemotron_or_meterless_clause_found"] = "either connected directly or through the Meterless engine" in decoded
        elif name == "nvidia_catalog":
            data = json.loads(text)
            result["nemotron_model_ids"] = [model["id"] for model in data.get("data", []) if "nemotron" in model["id"].lower()]
            result["limitation"] = "catalog metadata only; no authenticated inference or free allowance verified"
        elif name == "cisa_kev":
            data = json.loads(text)
            assert len(data["vulnerabilities"]) == data["count"]
            required = {"cveID", "vendorProject", "product", "dateAdded", "requiredAction"}
            assert all(required <= row.keys() for row in data["vulnerabilities"])
            result.update(catalog_version=data.get("catalogVersion"), catalog_date=data.get("dateReleased"),
                          record_count=data["count"], required_fields_valid=True)
    except urllib.error.HTTPError as error:
        result.update(status="BLOCKED", http_status=error.code, reason="HTTP access denied or unavailable")
    except Exception as error:
        # Exception text can contain IPs, query strings or proxy details; keep only its type.
        result.update(status="BLOCKED", error_type=type(error).__name__)
    return result


if __name__ == "__main__":
    records = list(ThreadPoolExecutor(max_workers=6).map(retrieve, SOURCES.items()))
    path = ROOT / "docs/evidence/public-sources.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    for row in records:
        print(row["id"], row["status"], row.get("http_status", row.get("error_type")), row.get("record_count", ""))
