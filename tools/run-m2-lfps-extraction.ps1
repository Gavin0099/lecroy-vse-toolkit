param(
    [Parameter(Mandatory = $true)]
    [string] $TracePath,

    [Parameter(Mandatory = $true)]
    [string] $ScriptPath,

    [Parameter(Mandatory = $true)]
    [string] $OutputPath
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $TracePath -PathType Leaf)) {
    throw "Trace file does not exist: $TracePath"
}

if (Test-Path -LiteralPath $OutputPath) {
    throw "Refusing to overwrite existing output: $OutputPath"
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory -and -not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

function Get-TraceSnapshot {
    param([string] $Path)

    for ($attempt = 1; $attempt -le 20; $attempt++) {
        try {
            $item = Get-Item -LiteralPath $Path
            $hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
            return [pscustomobject]@{
                Hash = $hash
                Size = $item.Length
                Mtime = $item.LastWriteTimeUtc.ToString('o')
            }
        }
        catch {
            if ($attempt -eq 20) {
                throw
            }
            Start-Sleep -Milliseconds 250
        }
    }
}

$before = Get-TraceSnapshot -Path $TracePath
$beforeHash = $before.Hash
$beforeSize = $before.Size
$beforeMtime = $before.Mtime

Add-Type -Path (Join-Path $PSScriptRoot 'm2-lfps-extraction.cs')
$result = [M2LfpsRunner]::Run($TracePath, $ScriptPath)
[GC]::Collect()
[GC]::WaitForPendingFinalizers()
[GC]::Collect()

$after = Get-TraceSnapshot -Path $TracePath
$afterHash = $after.Hash
$afterSize = $after.Size
$afterMtime = $after.Mtime
$traceIntegrityUnchanged = (
    $beforeHash -eq $afterHash -and
    $beforeSize -eq $afterSize -and
    $beforeMtime -eq $afterMtime
)

$artifact = [ordered]@{
    trace = $TracePath
    script = $ScriptPath
    run_result = $result.RunResult
    finished_result = $result.FinishedResult
    elapsed_milliseconds = $result.ElapsedMilliseconds
    notify_count = $result.NotifyCount
    summary_count = $result.SummaryCount
    declared_event_count = $result.DeclaredEventCount
    target_event_count = $result.Events.Count
    events = $result.Events
    reports = $result.Reports
    trace_integrity_unchanged = $traceIntegrityUnchanged
    before = [ordered]@{
        sha256 = $beforeHash
        size = $beforeSize
        mtime_utc = $beforeMtime
    }
    after = [ordered]@{
        sha256 = $afterHash
        size = $afterSize
        mtime_utc = $afterMtime
    }
    error = $result.Error
}

$json = $artifact | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText(
    $OutputPath,
    $json + [Environment]::NewLine,
    [System.Text.UTF8Encoding]::new($false)
)

$readBack = $null
$readBackValid = $true
try {
    $readBack = Get-Content -LiteralPath $OutputPath -Raw | ConvertFrom-Json
}
catch {
    $readBackValid = $false
}

$readBackMatch = (
    $readBackValid -and
    $readBack.run_result -eq $artifact.run_result -and
    $readBack.target_event_count -eq $artifact.target_event_count -and
    $readBack.declared_event_count -eq $artifact.declared_event_count -and
    $readBack.events.Count -eq $artifact.events.Count
)

$eventFieldsValid = $false
if ($artifact.events.Count -gt 0) {
    $eventFieldsValid = $true
    foreach ($event in $artifact.events) {
        if ($event.Index -lt 0 -or
            [string]::IsNullOrWhiteSpace($event.Timestamp) -or
            $event.Type -ne '_USB3_LFPS' -or
            $event.LfpsType -lt 0 -or
            $event.DurationNs -lt 0 -or
            $event.DurationSec -lt 0 -or
            $event.DurationRemainderNs -lt 0 -or
            $event.PatternType -lt 0 -or
            ($event.StartsPattern -ne 0 -and $event.StartsPattern -ne 1)) {
            $eventFieldsValid = $false
            break
        }
    }
}

$accepted = (
    $result.Error -eq '' -and
    $result.RunResult -eq 2 -and
    $result.SummaryCount -eq 1 -and
    $result.DeclaredEventCount -eq $result.Events.Count -and
    $result.Events.Count -gt 0 -and
    $readBackValid -and
    $readBackMatch -and
    $eventFieldsValid -and
    $traceIntegrityUnchanged
)

[pscustomobject]@{
    output_path = $OutputPath
    run_result = $result.RunResult
    finished_result = $result.FinishedResult
    elapsed_milliseconds = $result.ElapsedMilliseconds
    notify_count = $result.NotifyCount
    summary_count = $result.SummaryCount
    declared_event_count = $result.DeclaredEventCount
    target_event_count = $result.Events.Count
    json_exists = Test-Path -LiteralPath $OutputPath -PathType Leaf
    valid_json = $readBackValid
    read_back_match = $readBackMatch
    event_fields_valid = $eventFieldsValid
    trace_integrity_unchanged = $traceIntegrityUnchanged
    before_sha256 = $beforeHash
    after_sha256 = $afterHash
    before_size = $beforeSize
    after_size = $afterSize
    error = $result.Error
} | ConvertTo-Json -Compress

if (-not $accepted) {
    exit 1
}
