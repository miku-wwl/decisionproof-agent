"""Create and verify an allowlisted P0 review archive; never include private state."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "P0_EXECUTION_REPORT", "OFFICIAL_RULES", "AIG_V020_DEPENDENCY_VERIFICATION",
    "SPONSOR_READINESS", "PRODUCT_SELECTION", "SYSTEM_ARCHITECTURE",
    "ENVIRONMENT_SETUP", "RISK_REGISTER", "BUILD_SCHEDULE", "P1_EXECUTION_PROMPT",
)
PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\b(?:nvapi-|sk-|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{16,}"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"https?://[^/\s:@]+:[^/@\s]+@"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    for name in REQUIRED:
        assert (ROOT / "docs" / (name + ".md")).stat().st_size > 100, name
    subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", "AGENTS.md", "README.md", "LICENSE"],
                   cwd=ROOT, check=True, capture_output=True)
    paths = [ROOT / name for name in ("AGENTS.md", "README.md", "LICENSE", ".gitignore", ".env.example", "pyproject.toml", "uv.lock")]
    paths += sorted((ROOT / "docs").glob("*.md"))
    paths += sorted((ROOT / "docs/templates").glob("*.md"))
    paths += sorted((ROOT / "docs/evidence").glob("*.json"))
    paths += sorted((ROOT / "docs/evidence").glob("*.xml"))
    paths += sorted((ROOT / "docs/evidence").glob("*.txt"))
    paths += [ROOT / "scripts" / name for name in ("Invoke-P0Checks.ps1", "p0_public_sources.py", "package_p0.py")]
    paths += [ROOT / "tests/preflight/test_aig_dependency.py"]
    report_path = ROOT / "docs/evidence/package-verification.json"
    paths = [path for path in paths if path != report_path]
    content = {}
    for path in paths:
        assert not path.is_symlink()
        relative = path.relative_to(ROOT).as_posix()
        assert not any(part in (".preflight", ".venv", ".git", "private") for part in Path(relative).parts)
        assert not relative.endswith((".sqlite3", ".db", ".env"))
        data = path.read_bytes()
        assert not any(pattern.search(data) for pattern in PATTERNS), f"Potential credential pattern in {relative}"
        content[relative] = data
    # Templates deliberately have empty credentials; reject nonempty assignments.
    for line in content[".env.example"].decode().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            name, value = line.split("=", 1)
            if any(word in name for word in ("KEY", "TOKEN", "SECRET")):
                assert not value.strip(), name
    evidence = json.loads(content["docs/evidence/aig-smoke.json"])
    assert len(evidence["checks"]) == 5
    assert all(value["status"] == "PASS" for value in evidence["checks"].values())
    junit = content["docs/evidence/p0-tests.xml"]
    assert b'tests="5"' in junit and b'failures="0"' in junit and b'errors="0"' in junit
    local_targets = set(content) | {"docs/evidence/package-verification.json"}
    for relative, data in content.items():
        if not relative.endswith(".md"):
            continue
        for target in re.findall(r"\]\(([^)]+)\)", data.decode("utf-8")):
            if target.startswith(("https:", "http:", "#")):
                continue
            target_path = (ROOT / relative).parent / target.split("#")[0]
            assert target_path.resolve().relative_to(ROOT).as_posix() in local_targets, (relative, target)
    hashes = {name: digest(data) for name, data in content.items()}
    report = {"status": "PASS", "kind": "local review package only", "required_reports": 10,
              "payload_files_excluding_this_report": len(content), "payload_sha256": hashes,
              "credential_pattern_scan": "PASS (bounded patterns and explicit allowlist; not an account-wide secret audit)",
              "protected_original_files": "unchanged against HEAD", "local_markdown_links": "PASS",
              "zip_crc_and_entry_hashes": "PASS; checked after final write",
              "excluded": [".git", ".venv", ".preflight", "private stores/tokens", "raw website snapshots", "private .env files"]}
    content["docs/evidence/package-verification.json"] = (json.dumps(report, indent=2) + "\n").encode()
    folder = ROOT / "artifacts"
    folder.mkdir(exist_ok=True)
    archive = folder / "decisionproof-p0-review-2026-10-20-final.zip"
    if archive.exists():
        archive = folder / ("decisionproof-p0-review-2026-10-20-final-" + str(uuid4())[:8] + ".zip")
    with ZipFile(archive, "x", compression=ZIP_DEFLATED) as zipped:
        for name, data in sorted(content.items()):
            zipped.writestr(name, data)
    with ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert set(zipped.namelist()) == set(content)
        assert len(zipped.namelist()) == len(content)
        for name, data in content.items():
            assert digest(zipped.read(name)) == digest(data), name
    report_path.write_bytes(content["docs/evidence/package-verification.json"])
    archive_hash = digest(archive.read_bytes())
    archive.with_suffix(".zip.sha256").write_text(archive_hash + "  " + archive.name + "\n", encoding="ascii")
    print(json.dumps({"status": "PASS", "archive": str(archive), "entries": len(content),
                      "bytes": archive.stat().st_size, "sha256": archive_hash,
                      "verified_utc": datetime.now(timezone.utc).isoformat()}, indent=2))


if __name__ == "__main__":
    main()
