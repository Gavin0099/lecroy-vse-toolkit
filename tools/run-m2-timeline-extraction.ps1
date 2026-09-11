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

Add-Type -Path (Join-Path $PSScriptRoot 'm2-timeline-extraction.cs')
$result = [M2TimelineRunner]::Run($TracePath, $ScriptPath)
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
    declared_link_cmd_count = $result.DeclaredLinkCommandCount
    declared_ltssm_count = $result.DeclaredLtssmCount
    declared_lfps_count = $result.DeclaredLfpsCount
    declared_total_count = $result.DeclaredTotalCount
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
    $readBack.declared_total_count -eq $artifact.declared_total_count -and
    $readBack.events.Count -eq $artifact.events.Count
)

$reconstructedLinkCount = @($artifact.events | Where-Object { $_.EventClass -eq 'LINK_CMD' }).Count
$reconstructedLtssmCount = @($artifact.events | Where-Object { $_.EventClass -eq 'LTSSM_STATE' }).Count
$reconstructedLfpsCount = @($artifact.events | Where-Object { $_.EventClass -eq 'LFPS' }).Count
$reconstructedTotalCount = $reconstructedLinkCount + $reconstructedLtssmCount + $reconstructedLfpsCount
$summaryCountsMatch = (
    $result.DeclaredLinkCommandCount -eq $reconstructedLinkCount -and
    $result.DeclaredLtssmCount -eq $reconstructedLtssmCount -and
    $result.DeclaredLfpsCount -eq $reconstructedLfpsCount -and
    $result.DeclaredTotalCount -eq $reconstructedTotalCount -and
    $result.Events.Count -eq $reconstructedTotalCount
)

$eventFieldsValid = $false
$chronologicalOrderValid = $false
$timestampComponentsValid = $false
if ($artifact.events.Count -gt 0) {
    $eventFieldsValid = $true
    $chronologicalOrderValid = $true
    $timestampComponentsValid = $true
    $previousIndex = -1
    $previousTimestampNs = -1

    foreach ($event in $artifact.events) {
        if ($event.Index -lt 0 -or
            $event.Index -lt $previousIndex -or
            [string]::IsNullOrWhiteSpace($event.Timestamp) -or
            ($event.EventClass -eq 'LINK_CMD' -and $event.Type -ne '_USB3_LINK_CMD') -or
            ($event.EventClass -eq 'LTSSM_STATE' -and $event.Type -ne '_USB3_LTSSM_STATE') -or
            ($event.EventClass -eq 'LFPS' -and $event.Type -ne '_USB3_LFPS')) {
            $eventFieldsValid = $false
            $chronologicalOrderValid = $false
            break
        }

        if ($event.TimestampSeconds -lt 0 -or
            $event.TimestampNanoseconds -lt 0 -or
            $event.TimestampNanoseconds -ge 1000000000 -or
            $event.TimestampNs -lt 0) {
            $timestampComponentsValid = $false
            $chronologicalOrderValid = $false
            break
        }

        if ($event.TimestampNs -lt $previousTimestampNs) {
            $chronologicalOrderValid = $false
            break
        }

        if ($event.EventClass -eq 'LFPS') {
            if ($null -eq $event.Raw -or
                $event.Raw.LfpsType -lt 0 -or
                $event.Raw.DurationNs -lt 0 -or
                $event.Raw.DurationSec -lt 0 -or
                $event.Raw.DurationRemainderNs -lt 0 -or
                $event.Raw.PatternType -lt 0 -or
                ($event.Raw.StartsPattern -ne 0 -and $event.Raw.StartsPattern -ne 1)) {
                $eventFieldsValid = $false
                break
            }
        }
        elseif ($null -ne $event.Raw) {
            $eventFieldsValid = $false
            break
        }

        $previousIndex = $event.Index
        $previousTimestampNs = $event.TimestampNs
    }
}

$accepted = (
    $result.Error -eq '' -and
    $result.RunResult -eq 2 -and
    $result.SummaryCount -eq 1 -and
    $summaryCountsMatch -and
    $readBackValid -and
    $readBackMatch -and
    $eventFieldsValid -and
    $timestampComponentsValid -and
    $chronologicalOrderValid -and
    $traceIntegrityUnchanged
)

[pscustomobject]@{
    output_path = $OutputPath
    run_result = $result.RunResult
    finished_result = $result.FinishedResult
    elapsed_milliseconds = $result.ElapsedMilliseconds
    notify_count = $result.NotifyCount
    summary_count = $result.SummaryCount
    declared_link_cmd_count = $result.DeclaredLinkCommandCount
    declared_ltssm_count = $result.DeclaredLtssmCount
    declared_lfps_count = $result.DeclaredLfpsCount
    declared_total_count = $result.DeclaredTotalCount
    target_event_count = $result.Events.Count
    summary_counts_match = $summaryCountsMatch
    timestamp_components_valid = $timestampComponentsValid
    chronological_order_valid = $chronologicalOrderValid
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
