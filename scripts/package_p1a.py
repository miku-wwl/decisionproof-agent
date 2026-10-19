"""Explicit safe P1A review package; never package private state or credentials."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from uuid import uuid4
import xml.etree.ElementTree as ET
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]


def digest(data):return hashlib.sha256(data).hexdigest()


def main():
    baseline=json.loads((ROOT/'docs/evidence/p1a/session-baseline.json').read_text('utf-8'))['initial_head']
    subprocess.run(['git','merge-base','--is-ancestor',baseline,'HEAD'],cwd=ROOT,check=True,capture_output=True)
    protected=['AGENTS.md','LICENSE']+[str(p.relative_to(ROOT)) for p in (ROOT/'docs').glob('*.md') if p.name in ('P0_EXECUTION_REPORT.md','OFFICIAL_RULES.md','AIG_V020_DEPENDENCY_VERIFICATION.md','SPONSOR_READINESS.md','PRODUCT_SELECTION.md','SYSTEM_ARCHITECTURE.md','ENVIRONMENT_SETUP.md','RISK_REGISTER.md','BUILD_SCHEDULE.md','P1_EXECUTION_PROMPT.md')]
    subprocess.run(['git','diff','--exit-code',baseline,'--',*protected],cwd=ROOT,check=True,capture_output=True)
    suite_path=ROOT/'docs/evidence/p1a/all-tests.xml'
    suite=ET.parse(suite_path)
    for s in suite.iter('testsuite'):
        assert s.get('failures')=='0' and s.get('errors')=='0'
        s.set('hostname','REDACTED-LOCAL-HOST')
    suite.write(suite_path,encoding='utf-8',xml_declaration=True)
    assert json.loads((ROOT/'docs/evidence/p1a/browser-result.json').read_text('utf-8'))['status']=='PASS'
    frozen=json.loads((ROOT/'docs/evidence/p1a/scenario-specification.json').read_text('utf-8'))
    assert frozen['sha256']==digest((ROOT/'fixtures/scenarios.json').read_bytes())
    paths=[ROOT/p for p in ('README.md','AGENTS.md','LICENSE','.gitignore','.env.example','pyproject.toml','uv.lock')]
    allowed={'.py','.md','.json','.xml','.txt','.html','.css','.js','.png'}
    for folder in ('decisionproof','fixtures','tests','scripts','docs'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in allowed and '__pycache__' not in p.parts)
    report_path=ROOT/'docs/evidence/p1a/package-verification.json'
    paths=[p for p in paths if p!=report_path and p.name!='product-tests.xml']
    patterns=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'\b(?:nvapi-|sk-|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{16,}',rb'\bAKIA[0-9A-Z]{16}\b',rb'https?://[^/\s:@]+:[^/@\s]+@']
    payload={}
    for path in paths:
        assert not path.is_symlink()
        name=path.relative_to(ROOT).as_posix()
        assert not any(part in ('.git','.venv','.preflight','private','artifacts') for part in path.relative_to(ROOT).parts)
        data=path.read_bytes()
        if path.suffix!='.png':
            assert not any(re.search(pattern,data) for pattern in patterns),name
        payload[name]=data
    for line in payload['.env.example'].decode().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key,value=line.split('=',1)
            if any(word in key for word in ('KEY','TOKEN','SECRET')):assert not value.strip()
    # Package only the final suite; its host label is redacted, outcomes untouched.
    targets=set(payload)|{'docs/evidence/p1a/package-verification.json'}
    for name,data in payload.items():
        if not name.endswith('.md'):continue
        for target in re.findall(r'\]\(([^)]+)\)',data.decode('utf-8')):
            if target.startswith(('https:','http:','#')):continue
            target_path=((ROOT/name).parent/target.split('#')[0]).resolve()
            assert target_path.relative_to(ROOT).as_posix() in targets,(name,target)
    report={'status':'PASS','kind':'offline P1A sanitized review package','payload_files_excluding_this_manifest':len(payload),
        'payload_sha256':{name:digest(data) for name,data in payload.items()},'crc_and_entry_hashes':'PASS after final archive write',
        'frozen_scenario_hash_unchanged':True,'protected_P0_reports_and_AGENTS_LICENSE':'unchanged',
        'credential_scan':'bounded patterns + empty template checks; not an account-wide audit',
        'excluded':['private .env/capability/auth files','sandbox SQLite stores','server logs','.venv','.preflight','.git','interim product-tests.xml']}
    payload['docs/evidence/p1a/package-verification.json']=(json.dumps(report,indent=2)+'\n').encode()
    folder=ROOT/'artifacts';folder.mkdir(exist_ok=True)
    archive=folder/'decisionproof-p1a-v2-review-2026-10-20.zip'
    if archive.exists():archive=folder/f'decisionproof-p1a-v2-review-2026-10-20-{str(uuid4())[:8]}.zip'
    with ZipFile(archive,'x',compression=ZIP_DEFLATED) as zipped:
        for name,data in sorted(payload.items()):zipped.writestr(name,data)
    with ZipFile(archive) as zipped:
        assert zipped.testzip() is None and set(zipped.namelist())==set(payload)
        assert len(zipped.namelist())==len(payload)
        for name,data in payload.items():assert digest(zipped.read(name))==digest(data),name
    report_path.write_bytes(payload['docs/evidence/p1a/package-verification.json'])
    checksum=digest(archive.read_bytes())
    archive.with_suffix('.zip.sha256').write_text(checksum+'  '+archive.name+'\n',encoding='ascii')
    print(json.dumps({'status':'PASS','archive':str(archive),'entries':len(payload),'bytes':archive.stat().st_size,'sha256':checksum},indent=2))


if __name__=='__main__':main()
