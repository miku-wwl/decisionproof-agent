param([string]$AigReference)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$evidence = Join-Path (Get-Location) 'docs\evidence'
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
uv sync --locked --python 3.13 --link-mode copy
if ($LASTEXITCODE -ne 0) { throw 'uv sync failed' }
uv lock --check --offline
if ($LASTEXITCODE -ne 0) { throw 'lock verification failed' }
uv pip check
if ($LASTEXITCODE -ne 0) { throw 'dependency consistency failed' }
if (-not $AigReference) {
    $cache = (uv cache dir).Trim()
    $candidates = rg --files (Join-Path $cache 'git-v0\checkouts') -g app.py |
        Where-Object { $_ -match '[\\/]examples[\\/]consumer[\\/]app\.py$' }
    foreach ($file in $candidates) {
        $candidate = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $file))
        $sha = (git -C $candidate rev-parse HEAD).Trim()
        if ($sha -eq '7261fdd2f47d2b15fabe8faac527eeee37338eb1') { $AigReference = $candidate; break }
    }
}
if (-not $AigReference) { throw 'Pinned external reference example not found; supply -AigReference' }
$env:P0_AIG_REFERENCE = $AigReference
& .\.venv\Scripts\python.exe -I -m pytest tests/preflight -q --junitxml=docs/evidence/p0-tests.xml
if ($LASTEXITCODE -ne 0) { throw 'P0 dependency tests failed' }
[xml]$junit = Get-Content -LiteralPath (Join-Path $evidence 'p0-tests.xml') -Raw
foreach ($suite in $junit.SelectNodes('//testsuite')) {
    if ($suite.HasAttribute('hostname')) { $suite.SetAttribute('hostname','REDACTED-LOCAL-HOST') }
}
$junit.Save((Join-Path $evidence 'p0-tests.xml'))
$checks = [ordered]@{}
foreach ($name in @('git','uv','python','node','npm','docker','cursor')) {
    $command = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
    $checks[$name] = [ordered]@{ found = [bool]$command; path = $command.Source }
}
$versions = [ordered]@{ git=(git --version); uv=(uv --version); python=(& .\.venv\Scripts\python.exe --version); node=(node --version); npm=(npm --version) }
$docker = docker version --format '{{json .}}' | ConvertFrom-Json
$credentials = @()
foreach ($scope in @('Process','User','Machine')) {
    $credentials += @([Environment]::GetEnvironmentVariables($scope).GetEnumerator() |
        Where-Object Key -Match 'ZETARIS|NVIDIA|NEMOTRON|METERLESS|CURSOR' |
        ForEach-Object { [ordered]@{scope=$scope; name=$_.Key; configured=(-not [string]::IsNullOrWhiteSpace($_.Value))} })
}
$os = Get-CimInstance Win32_OperatingSystem
$result = [ordered]@{
    observed_utc=[DateTimeOffset]::UtcNow.ToString('o'); client_date='2026-10-20'; timezone='Pacific/Auckland';
    os=$os.Caption; os_version=$os.Version; architecture=$os.OSArchitecture;
    powershell=$PSVersionTable.PSVersion.ToString(); tools=$checks; versions=$versions;
    docker_client=$docker.Client.Version; docker_engine=$docker.Server.Version; docker_context=$docker.Client.Context;
    sponsor_environment_names_only=$credentials;
    limits=@('No private credential files or browser cookies searched','Cursor command absent is not proof of no installation','Docker workload and browser UI not tested')
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidence 'environment.json') -Encoding utf8
& .\.venv\Scripts\python.exe -I scripts/p0_public_sources.py
if ($LASTEXITCODE -ne 0) { throw 'Source evidence collection failed' }
