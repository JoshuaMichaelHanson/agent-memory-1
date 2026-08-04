$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command"
    }
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$Python = Join-Path $VenvPath "Scripts\python.exe"
$TempPath = Join-Path $ProjectRoot "tmp\python-temp"

New-Item -ItemType Directory -Force -Path $TempPath | Out-Null
$env:TEMP = $TempPath
$env:TMP = $TempPath
$env:TMPDIR = $TempPath

if (-not (Test-Path $Python)) {
    Invoke-Checked { python -m venv $VenvPath }
}

Push-Location $ProjectRoot
try {
    Invoke-Checked { & $Python -m ensurepip --upgrade --default-pip }
    Invoke-Checked { & $Python -m pip install --upgrade pip }
    Invoke-Checked { & $Python -m pip install -e ".[dev]" }
    Invoke-Checked { & $Python -m agent_memory --help | Out-Null }
    Invoke-Checked { & (Join-Path $VenvPath "Scripts\agent-memory.exe") --help | Out-Null }
    Invoke-Checked { & $Python -m pytest }
}
finally {
    Pop-Location
}


