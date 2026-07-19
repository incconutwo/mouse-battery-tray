[CmdletBinding()]
param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvRoot = Join-Path $repoRoot '.build-venv'
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'

Push-Location $repoRoot
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        python -m venv $venvRoot
    }

    & $venvPython -m pip install --disable-pip-version-check --requirement (Join-Path $repoRoot 'requirements-build.txt')
    & $venvPython (Join-Path $repoRoot 'build_icon.py')
    & $venvPython -m PyInstaller --noconfirm --clean (Join-Path $repoRoot 'AttackSharkBatteryTray.spec')

    if (-not $SkipInstaller) {
        $isccCandidates = @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
            (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
            (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
        )
        $iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $iscc) {
            throw 'Inno Setup 6 was not found. Install JRSoftware.InnoSetup with winget or rerun with -SkipInstaller.'
        }
        & $iscc (Join-Path $repoRoot 'installer.iss')
    }

    Write-Output 'Build completed.'
}
finally {
    Pop-Location
}
