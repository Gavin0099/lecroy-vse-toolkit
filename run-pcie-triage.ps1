param(
    [Parameter(Mandatory = $true)][string]$InputManifest,
    [Parameter(Mandatory = $true)][string]$OutputDir
)
# Thin wrapper for the offline PCIe triage runner (PCIe-G9a).
# Input: a verified extraction bundle manifest. No PETracer GUI, COM, .pex or VSE is used here.
$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'scripts\pcie\run_pcie_triage.py'
& python -X utf8 -B $runner --input-manifest $InputManifest --output-dir $OutputDir
exit $LASTEXITCODE
