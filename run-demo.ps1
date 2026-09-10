<#!
.SYNOPSIS
    Run the qualified PASS/FAIL LeCroy triage Demo end to end.

.DESCRIPTION
    The source traces are treated as immutable evidence. This runner records
    their identity, creates separate read-only sandbox copies, runs the same
    combined VSE extractor for both copies, compares the resulting timelines,
    and writes a human-readable report.

    The output directory must not already exist. This prevents accidental
    overwrite of prior evidence.
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

function Get-FileSnapshot {
    param([Parameter(Mandatory = $true)][string] $Path)

    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($item.PSIsContainer) {
        throw "Expected a file: $Path"
    }

    return [ordered]@{
        path = $item.FullName
        sha256 = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash
        size = $item.Length
        mtime_utc = $item.LastWriteTimeUtc.ToString('o')
    }
}

function Test-SnapshotUnchanged {
    param(
        [Parameter(Mandatory = $true)] $Before,
        [Parameter(Mandatory = $true)] $After
    )

    return (
        $Before.sha256 -eq $After.sha256 -and
        $Before.size -eq $After.size -and
        $Before.mtime_utc -eq $After.mtime_utc
    )
}

function Set-ReadOnlyWorkingCopy {
    param([Parameter(Mandatory = $true)][string] $SourcePath,
        [Parameter(Mandatory = $true)][string] $DestinationPath)

    $destinationDirectory = Split-Path -Parent $DestinationPath
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath
    Set-ItemProperty -LiteralPath $DestinationPath -Name IsReadOnly -Value $true

    $item = Get-Item -LiteralPath $DestinationPath
    if (-not $item.IsReadOnly) {
        throw "Could not mark working copy read-only: $DestinationPath"
    }
}

function Invoke-TimelineExtraction {
    param(
        [Parameter(Mandatory = $true)][string] $TracePath,
        [Parameter(Mandatory = $true)][string] $TimelinePath,
        [Parameter(Mandatory = $true)][string] $LogPath
    )

    $scriptPath = Join-Path $PSScriptRoot 'scripts\m2-packet-extraction-4.vse'
    $runnerPath = Join-Path $PSScriptRoot 'tools\run-m2-timeline-extraction.ps1'

    $global:LASTEXITCODE = 0
    $runOutput = @(
        & $runnerPath `
            -TracePath $TracePath `
            -ScriptPath $scriptPath `
            -OutputPath $TimelinePath `
            2>&1
    )
    $runExitCode = $LASTEXITCODE
    $runOutput | Set-Content -LiteralPath $LogPath -Encoding UTF8

    if ($runExitCode -ne 0) {
        throw "Timeline extraction failed for $TracePath. See $LogPath"
    }

    return (Get-Content -LiteralPath $TimelinePath -Raw | ConvertFrom-Json)
}

function Convert-WindowToText {
    param($Window)

    if ($null -eq $Window) {
        return 'N/A'
    }

    return ('{0:N3} - {1:N3} sec' -f
        [double]$Window.start_seconds,
        [double]$Window.end_seconds)
}

function Get-CountValue {
    param($Counts, [string] $Name)

    $value = $Counts.PSObject.Properties[$Name]
    if ($null -eq $value) {
        return 0
    }

    return [int]$value.Value
}

$passSourcePath = Convert-ToAbsolutePath -Path $PassTrace
$failSourcePath = Convert-ToAbsolutePath -Path $FailTrace
$outputDirectory = Convert-ToAbsolutePath -Path $Output

if (-not (Test-Path -LiteralPath $passSourcePath -PathType Leaf)) {
    throw "PASS trace does not exist: $passSourcePath"
}

if (-not (Test-Path -LiteralPath $failSourcePath -PathType Leaf)) {
    throw "FAIL trace does not exist: $failSourcePath"
}

if ($passSourcePath -eq $failSourcePath) {
    throw 'PASS and FAIL traces must be different files.'
}

if (Test-Path -LiteralPath $outputDirectory) {
    throw "Refusing to overwrite existing output directory: $outputDirectory"
}

$passBefore = Get-FileSnapshot -Path $passSourcePath
$failBefore = Get-FileSnapshot -Path $failSourcePath

New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$sandboxDirectory = Join-Path $outputDirectory 'sandbox'
$logsDirectory = Join-Path $outputDirectory 'logs'
New-Item -ItemType Directory -Path $sandboxDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $logsDirectory -Force | Out-Null

$passWorkingPath = Join-Path $sandboxDirectory (Join-Path 'pass' ([System.IO.Path]::GetFileName($passSourcePath)))
$failWorkingPath = Join-Path $sandboxDirectory (Join-Path 'fail' ([System.IO.Path]::GetFileName($failSourcePath)))
Set-ReadOnlyWorkingCopy -SourcePath $passSourcePath -DestinationPath $passWorkingPath
Set-ReadOnlyWorkingCopy -SourcePath $failSourcePath -DestinationPath $failWorkingPath

$passTimelinePath = Join-Path $outputDirectory 'pass-timeline.json'
$failTimelinePath = Join-Path $outputDirectory 'fail-timeline.json'
$comparisonPath = Join-Path $outputDirectory 'comparison.json'
$sourceIntegrityPath = Join-Path $outputDirectory 'source-integrity.json'
$reportPath = Join-Path $outputDirectory 'report.md'

$passTimeline = Invoke-TimelineExtraction `
    -TracePath $passWorkingPath `
    -TimelinePath $passTimelinePath `
    -LogPath (Join-Path $logsDirectory 'pass-extraction.log')

$failTimeline = Invoke-TimelineExtraction `
    -TracePath $failWorkingPath `
    -TimelinePath $failTimelinePath `
    -LogPath (Join-Path $logsDirectory 'fail-extraction.log')

$passAfter = Get-FileSnapshot -Path $passSourcePath
$failAfter = Get-FileSnapshot -Path $failSourcePath
$passSourceUnchanged = Test-SnapshotUnchanged -Before $passBefore -After $passAfter
$failSourceUnchanged = Test-SnapshotUnchanged -Before $failBefore -After $failAfter

$sourceIntegrity = [ordered]@{
    pass = [ordered]@{
        before = $passBefore
        after = $passAfter
        unchanged = $passSourceUnchanged
    }
    fail = [ordered]@{
        before = $failBefore
        after = $failAfter
        unchanged = $failSourceUnchanged
    }
    source_evidence_integrity = ($passSourceUnchanged -and $failSourceUnchanged)
    claim_boundary = 'Source evidence integrity is qualified for this run; universal immutability is not claimed.'
}
[System.IO.File]::WriteAllText(
    $sourceIntegrityPath,
    (($sourceIntegrity | ConvertTo-Json -Depth 10) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false))

if (-not $sourceIntegrity.source_evidence_integrity) {
    throw "Source evidence integrity failed. See $sourceIntegrityPath"
}

$comparatorPath = Join-Path $PSScriptRoot 'tools\compare-m2-timelines.ps1'
$global:LASTEXITCODE = 0
$comparisonRunOutput = @(
    & $comparatorPath `
        -PassTimelinePath $passTimelinePath `
        -FailTimelinePath $failTimelinePath `
        -OutputPath $comparisonPath `
        2>&1
)
$comparisonExitCode = $LASTEXITCODE
$comparisonRunOutput | Set-Content -LiteralPath (Join-Path $logsDirectory 'comparison.log') -Encoding UTF8
if ($comparisonExitCode -ne 0) {
    throw "Timeline comparison failed. See $($logsDirectory)\comparison.log"
}

$comparison = Get-Content -LiteralPath $comparisonPath -Raw | ConvertFrom-Json
$candidate = $comparison.candidate_divergence
$anchor = $comparison.anchor
$anchorDetail = $anchor.status
if ($null -ne $anchor) {
    $anchorDetail = "$($anchor.status), length $($anchor.length)"
}

$reportLines = [System.Collections.Generic.List[string]]::new()
$reportLines.Add('# LeCroy PASS / FAIL Triage')
$reportLines.Add('')
$reportLines.Add('## Inputs')
$reportLines.Add('')
$reportLines.Add("- PASS source: $passSourcePath")
$reportLines.Add("- FAIL source: $failSourcePath")
$reportLines.Add('- Analysis mode: read-only sandbox working copies')
$reportLines.Add('')
$reportLines.Add('## Extracted events')
$reportLines.Add('')
$reportLines.Add('| Event class | PASS | FAIL |')
$reportLines.Add('| --- | ---: | ---: |')
$reportLines.Add("| LINK_CMD | $(Get-CountValue $comparison.pass_counts 'LINK_CMD') | $(Get-CountValue $comparison.fail_counts 'LINK_CMD') |")
$reportLines.Add("| LTSSM_STATE | $(Get-CountValue $comparison.pass_counts 'LTSSM_STATE') | $(Get-CountValue $comparison.fail_counts 'LTSSM_STATE') |")
$reportLines.Add("| LFPS | $(Get-CountValue $comparison.pass_counts 'LFPS') | $(Get-CountValue $comparison.fail_counts 'LFPS') |")
$reportLines.Add("| Total | $($comparison.pass_total) | $($comparison.fail_total) |")
$reportLines.Add('')
$reportLines.Add('## Candidate divergence')
$reportLines.Add('')
$reportLines.Add("- Common anchor: $anchorDetail")
$reportLines.Add("- Candidate status: $($candidate.status)")
$reportLines.Add("- PASS timestamp: $($candidate.pass_timestamp)")
$reportLines.Add("- FAIL timestamp: $($candidate.fail_timestamp)")
$reportLines.Add("- Suggested PASS GUI window: $(Convert-WindowToText $candidate.pass_suggested_window)")
$reportLines.Add("- Suggested FAIL GUI window: $(Convert-WindowToText $candidate.fail_suggested_window)")
$reportLines.Add('')
$reportLines.Add('## Source integrity')
$reportLines.Add('')
$reportLines.Add("- PASS source unchanged: $($passSourceUnchanged)")
$reportLines.Add("- FAIL source unchanged: $($failSourceUnchanged)")
$reportLines.Add('- Working copies: read-only')
$reportLines.Add('')
$reportLines.Add('## Claim boundary')
$reportLines.Add('')
$reportLines.Add('- Candidate divergence only.')
$reportLines.Add('- Root cause, severity, and automatic PASS/FAIL classification are not determined.')
$reportLines.Add('- Timestamps are trace-local and are not directly aligned across captures.')
$reportLines.Add('- Universal immutability across all traces and environments is not claimed.')

[System.IO.File]::WriteAllLines($reportPath, $reportLines, [System.Text.UTF8Encoding]::new($false))

$result = [ordered]@{
    status = 'PASS'
    pass_timeline = $passTimelinePath
    fail_timeline = $failTimelinePath
    comparison = $comparisonPath
    source_integrity = $sourceIntegrityPath
    report = $reportPath
    sandbox = $sandboxDirectory
    candidate_status = $candidate.status
    anchor_status = $anchor.status
    source_evidence_integrity = $sourceIntegrity.source_evidence_integrity
}
$result | ConvertTo-Json -Depth 10 -Compress
