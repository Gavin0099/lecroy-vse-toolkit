<#!
.SYNOPSIS
    Qualify DEMO-2 on a fresh Windows PowerShell 5.1 process.

.DESCRIPTION
    This harness is intended to be launched by powershell.exe, not pwsh. It
    compiles the COM host with the same Add-Type path used by the runner,
    parses the runner scripts, checks existing-output refusal in a child
    process, then launches the full runner in another fresh powershell.exe
    process.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $PassTrace,

    [Parameter(Mandatory = $true)]
    [string] $FailTrace,

    [Parameter(Mandatory = $true)]
    [string] $Output
)

$ErrorActionPreference = 'Stop'

function Convert-ToAbsolutePath {
    param([Parameter(Mandatory = $true)][string] $Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath(
        (Join-Path -Path (Get-Location).Path -ChildPath $Path))
}

function Assert-Parsed {
    param([Parameter(Mandatory = $true)][string] $Path)

    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref] $tokens,
        [ref] $errors) | Out-Null

    if ($errors.Count -gt 0) {
        throw "PowerShell parse failed: $Path`n$($errors | Out-String)"
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$passPath = Convert-ToAbsolutePath -Path $PassTrace
$failPath = Convert-ToAbsolutePath -Path $FailTrace
$outputPath = Convert-ToAbsolutePath -Path $Output
$runnerPath = Join-Path $repoRoot 'run-demo.ps1'
$hostSourcePath = Join-Path $repoRoot 'tools\m2-timeline-extraction.cs'
$timelineRunnerPath = Join-Path $repoRoot 'tools\run-m2-timeline-extraction.ps1'

if ($PSVersionTable.PSEdition -ne 'Desktop' -or
    $PSVersionTable.PSVersion.Major -ne 5 -or
    $PSVersionTable.PSVersion.Minor -ne 1) {
    throw "This harness requires Windows PowerShell 5.1; detected $($PSVersionTable.PSVersion) / $($PSVersionTable.PSEdition)."
}

if (-not (Test-Path -LiteralPath $passPath -PathType Leaf)) {
    throw "PASS trace does not exist: $passPath"
}

if (-not (Test-Path -LiteralPath $failPath -PathType Leaf)) {
    throw "FAIL trace does not exist: $failPath"
}

if (Test-Path -LiteralPath $outputPath) {
    throw "Output directory must not already exist: $outputPath"
}

Add-Type -Path $hostSourcePath
Assert-Parsed -Path $runnerPath
Assert-Parsed -Path $timelineRunnerPath

$windowsPowerShell = (Get-Command powershell.exe -ErrorAction Stop).Source
$refusalRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    'lecroy-demo2-existing-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $refusalRoot | Out-Null

$savedErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $refusalOutput = @(
        & $windowsPowerShell `
            -NoProfile `
            -NonInteractive `
            -ExecutionPolicy Bypass `
            -File $runnerPath `
            -PassTrace $passPath `
            -FailTrace $failPath `
            -Output $refusalRoot `
            2>&1
    )
    $refusalExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $savedErrorActionPreference
}
$refusalText = ($refusalOutput -join [Environment]::NewLine)
$refusalPassed = (
    $refusalExitCode -ne 0 -and
    $refusalText -match 'Refusing to overwrite existing output directory'
)
if (-not $refusalPassed) {
    throw "Existing-output refusal check failed. Exit=$refusalExitCode`n$refusalText"
}

$runnerLog = Join-Path $outputPath 'windows-powershell-run.log'
$savedErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $runnerOutput = @(
        & $windowsPowerShell `
            -NoProfile `
            -NonInteractive `
            -ExecutionPolicy Bypass `
            -File $runnerPath `
            -PassTrace $passPath `
            -FailTrace $failPath `
            -Output $outputPath `
            2>&1
    )
    $runnerExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $savedErrorActionPreference
}
$runnerOutput | Set-Content -LiteralPath $runnerLog -Encoding UTF8

if ($runnerExitCode -ne 0) {
    throw "DEMO-2 Windows PowerShell runner failed. See $runnerLog"
}

$integrityPath = Join-Path $outputPath 'source-integrity.json'
$comparisonPath = Join-Path $outputPath 'comparison.json'
$reportPath = Join-Path $outputPath 'report.md'
if (-not (Test-Path -LiteralPath $integrityPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $comparisonPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
    throw "DEMO-2 output artifacts are incomplete: $outputPath"
}

$integrity = Get-Content -LiteralPath $integrityPath -Raw | ConvertFrom-Json
$comparison = Get-Content -LiteralPath $comparisonPath -Raw | ConvertFrom-Json
if (-not $integrity.source_evidence_integrity) {
    throw 'DEMO-2 source evidence integrity was not PASS.'
}
if (-not $integrity.working_copy_integrity -or
    -not $integrity.analysis_input_integrity -or
    -not $integrity.working_copy.pass.unchanged -or
    -not $integrity.working_copy.fail.unchanged -or
    -not $integrity.working_copy.pass.before.is_readonly -or
    -not $integrity.working_copy.pass.after.is_readonly -or
    -not $integrity.working_copy.fail.before.is_readonly -or
    -not $integrity.working_copy.fail.after.is_readonly) {
    throw 'DEMO-2 working-copy integrity was not PASS.'
}

$compatibility = [ordered]@{
    status = 'PASS'
    host = [ordered]@{
        executable = $windowsPowerShell
        version = $PSVersionTable.PSVersion.ToString()
        edition = $PSVersionTable.PSEdition
        clr = [System.Environment]::Version.ToString()
    }
    add_type_compile = 'PASS'
    runner_parse = 'PASS'
    timeline_runner_parse = 'PASS'
    existing_output_refusal = 'PASS'
    full_runner_exit_code = $runnerExitCode
    source_evidence_integrity = $integrity.source_evidence_integrity
    anchor_status = $comparison.anchor.status
    candidate_status = $comparison.candidate_divergence.status
    working_copy_integrity = $integrity.working_copy_integrity
    analysis_input_integrity = $integrity.analysis_input_integrity
    output = $outputPath
    runner_log = $runnerLog
}
$compatibilityPath = Join-Path $outputPath 'windows-powershell-compatibility.json'
[System.IO.File]::WriteAllText(
    $compatibilityPath,
    (($compatibility | ConvertTo-Json -Depth 10) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false))

$compatibility | ConvertTo-Json -Depth 10 -Compress
