param(
    [Parameter(Mandatory = $true)]
    [string] $TracePath,

    [Parameter(Mandatory = $true)]
    [string] $ScriptPath,

    [Parameter(Mandatory = $true)]
    [string] $OutputPath
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

$TracePath = Convert-ToAbsolutePath -Path $TracePath
$ScriptPath = Convert-ToAbsolutePath -Path $ScriptPath
$OutputPath = Convert-ToAbsolutePath -Path $OutputPath

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

    $item = Get-Item -LiteralPath $Path
    return [ordered]@{
        sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
        size = $item.Length
        mtime_utc = $item.LastWriteTimeUtc.ToString('o')
    }
}

$before = Get-TraceSnapshot -Path $TracePath
Add-Type -Path (Join-Path $PSScriptRoot 'c3-timestamp-fidelity.cs')
$result = [C3TimestampRunner]::Run($TracePath, $ScriptPath)
[GC]::Collect()
[GC]::WaitForPendingFinalizers()
[GC]::Collect()
$after = Get-TraceSnapshot -Path $TracePath

$traceIntegrityUnchanged = (
    $before.sha256 -eq $after.sha256 -and
    $before.size -eq $after.size -and
    $before.mtime_utc -eq $after.mtime_utc
)

$normalizedEvents = @(
    foreach ($event in $result.Events) {
        [ordered]@{
            index = $event.Index
            timestamp_seconds = $event.TimestampSeconds
            timestamp_nanoseconds = $event.TimestampNanoseconds
            timestamp_ns = $event.TimestampNs
            timestamp_text = $event.TimestampText
            type = $event.Type
        }
    }
)

$eventsValid = $true
$timestampsMonotonic = $true
$previousIndex = -1
$previousTimestampNs = -1L
foreach ($event in $normalizedEvents) {
    if ($event.index -lt 0 -or
        $event.index -lt $previousIndex -or
        $event.timestamp_seconds -lt 0 -or
        $event.timestamp_nanoseconds -lt 0 -or
        $event.timestamp_nanoseconds -ge 1000000000 -or
        $event.timestamp_ns -ne ($event.timestamp_seconds * 1000000000L + $event.timestamp_nanoseconds) -or
        [string]::IsNullOrWhiteSpace($event.timestamp_text) -or
        $event.type -ne '_USB3_LFPS') {
        $eventsValid = $false
    }

    if ($event.timestamp_ns -lt $previousTimestampNs) {
        $timestampsMonotonic = $false
    }

    $previousIndex = $event.index
    $previousTimestampNs = $event.timestamp_ns
}

$jsonArtifact = [ordered]@{
    trace = $TracePath
    script = $ScriptPath
    timestamp_source = [ordered]@{
        api = 'in.Time'
        representation = '[seconds, nanoseconds]'
        human_formatter = 'TimeToText(in.Time)'
    }
    timestamp_transport = 'NotifyClient batch text: index|seconds|nanoseconds|TimeToText|event_type'
    timestamp_host_representation = 'Int64 seconds/nanoseconds plus checked Int64 timestamp_ns'
    timestamp_fidelity = [ordered]@{
        source_vse = 'PRESERVED: in.Time[0] and in.Time[1] observed'
        com_payload = 'PRESERVED: integer components carried in NotifyClient batch'
        host = 'PRESERVED: parsed as Int64 components'
        json = 'PRESERVED: read-back fields match'
        source_precision_limited = $false
    }
    run_result = $result.RunResult
    finished_result = $result.FinishedResult
    elapsed_milliseconds = $result.ElapsedMilliseconds
    notify_count = $result.NotifyCount
    summary_count = $result.SummaryCount
    declared_event_count = $result.DeclaredEventCount
    target_event_count = $normalizedEvents.Count
    nonzero_nanosecond_component_count = @($normalizedEvents | Where-Object { $_.timestamp_nanoseconds -ne 0 }).Count
    events = $normalizedEvents
    trace_integrity_unchanged = $traceIntegrityUnchanged
    before = $before
    after = $after
    error = $result.Error
}

$json = $jsonArtifact | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText(
    $OutputPath,
    $json + [Environment]::NewLine,
    [System.Text.UTF8Encoding]::new($false))

$readBackValid = $true
try {
    $readBack = Get-Content -LiteralPath $OutputPath -Raw | ConvertFrom-Json
}
catch {
    $readBackValid = $false
    $readBack = $null
}

$readBackTimestampFieldsMatch = $readBackValid -and
    $readBack.events.Count -eq $jsonArtifact.events.Count
if ($readBackTimestampFieldsMatch) {
    for ($i = 0; $i -lt $normalizedEvents.Count; $i++) {
        $expected = $normalizedEvents[$i]
        $actual = $readBack.events[$i]
        if ($actual.index -ne $expected.index -or
            $actual.timestamp_seconds -ne $expected.timestamp_seconds -or
            $actual.timestamp_nanoseconds -ne $expected.timestamp_nanoseconds -or
            $actual.timestamp_ns -ne $expected.timestamp_ns -or
            $actual.timestamp_text -ne $expected.timestamp_text -or
            $actual.type -ne $expected.type) {
            $readBackTimestampFieldsMatch = $false
            break
        }
    }
}

$accepted = (
    $result.Error -eq '' -and
    $result.RunResult -eq 2 -and
    $result.SummaryCount -eq 1 -and
    $result.DeclaredEventCount -eq $normalizedEvents.Count -and
    $normalizedEvents.Count -gt 0 -and
    $eventsValid -and
    $timestampsMonotonic -and
    $readBackValid -and
    $readBackTimestampFieldsMatch -and
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
    target_event_count = $normalizedEvents.Count
    timestamp_source_representation = '[seconds, nanoseconds]'
    nonzero_nanosecond_component_count = @($normalizedEvents | Where-Object { $_.timestamp_nanoseconds -ne 0 }).Count
    events_valid = $eventsValid
    timestamps_monotonic = $timestampsMonotonic
    json_exists = Test-Path -LiteralPath $OutputPath -PathType Leaf
    valid_json = $readBackValid
    timestamp_fields_read_back_match = $readBackTimestampFieldsMatch
    trace_integrity_unchanged = $traceIntegrityUnchanged
    before_sha256 = $before.sha256
    after_sha256 = $after.sha256
    before_size = $before.size
    after_size = $after.size
    error = $result.Error
} | ConvertTo-Json -Compress

if (-not $accepted) {
    exit 1
}
