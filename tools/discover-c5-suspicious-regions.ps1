param(
    [Parameter(Mandatory = $true)]
    [string] $PassTimelinePath,

    [Parameter(Mandatory = $true)]
    [string] $FailTimelinePath,

    [Parameter(Mandatory = $true)]
    [string] $OutputPath,

    [int] $TopK = 3
)

$ErrorActionPreference = 'Stop'

if ($TopK -lt 1) {
    throw 'TopK must be at least 1.'
}
if (-not (Test-Path -LiteralPath $PassTimelinePath -PathType Leaf)) {
    throw "PASS timeline does not exist: $PassTimelinePath"
}
if (-not (Test-Path -LiteralPath $FailTimelinePath -PathType Leaf)) {
    throw "FAIL timeline does not exist: $FailTimelinePath"
}
if (Test-Path -LiteralPath $OutputPath) {
    throw "Refusing to overwrite existing output: $OutputPath"
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory -and -not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$pass = Get-Content -LiteralPath $PassTimelinePath -Raw | ConvertFrom-Json
$fail = Get-Content -LiteralPath $FailTimelinePath -Raw | ConvertFrom-Json
$passEvents = @($pass.events)
$failEvents = @($fail.events)

$binNs = [int64]1000000
$windowNs = [int64]10000000
$strideNs = [int64]1000000
$rarePassGlobalCountThreshold = [int64]10

function Assert-TimelineInput {
    param($Timeline, [object[]] $Events, [string] $Name)

    if ($Timeline.trace_integrity_unchanged -ne $true) {
        throw "$Name timeline does not carry a passing trace-integrity result."
    }
    if ($Events.Count -eq 0) {
        throw "$Name timeline contains no events."
    }
    foreach ($event in $Events) {
        if ($null -eq $event.TimestampNs -or
            $null -eq $event.TimestampSeconds -or
            $null -eq $event.TimestampNanoseconds -or
            [int64]$event.TimestampNs -lt 0 -or
            [int64]$event.TimestampNanoseconds -lt 0 -or
            [int64]$event.TimestampNanoseconds -ge 1000000000) {
            throw "$Name timeline is missing valid timestamp_ns fields."
        }
    }
}

function Get-TraceStartNs {
    param([object[]] $Events)

    $minimum = [int64]::MaxValue
    foreach ($event in $Events) {
        if ([int64]$event.TimestampNs -lt $minimum) {
            $minimum = [int64]$event.TimestampNs
        }
    }
    return $minimum
}

function Get-TraceEndNs {
    param([object[]] $Events)

    $maximum = [int64]::MinValue
    foreach ($event in $Events) {
        if ([int64]$event.TimestampNs -gt $maximum) {
            $maximum = [int64]$event.TimestampNs
        }
    }
    return $maximum
}

function Get-LfpsRawSignature {
    param($Event)

    if ($Event.EventClass -ne 'LFPS' -or $null -eq $Event.Raw) {
        return $null
    }

    return ('{0}|{1}|{2}|{3}' -f
        [int64]$Event.Raw.LfpsType,
        [int64]$Event.Raw.PatternType,
        [int64]$Event.Raw.DurationNs,
        [int64]$Event.Raw.StartsPattern)
}

function Get-GlobalLfpsCounts {
    param([object[]] $Events)

    $counts = @{}
    foreach ($event in $Events) {
        $signature = Get-LfpsRawSignature -Event $event
        if ($null -eq $signature) {
            continue
        }
        if ($counts.ContainsKey($signature)) {
            $counts[$signature]++
        }
        else {
            $counts[$signature] = [int64]1
        }
    }
    return $counts
}

function New-EmptyBin {
    return [ordered]@{
        link_cmd = [int64]0
        ltssm_state = [int64]0
        lfps = [int64]0
        total = [int64]0
        rare_lfps = [int64]0
    }
}

function Build-Bins {
    param(
        [object[]] $Events,
        [int64] $TraceStartNs,
        [int64] $TraceEndNs,
        [hashtable] $PassGlobalCounts
    )

    $binCount = [int][Math]::Ceiling(([double]($TraceEndNs - $TraceStartNs + 1)) / $binNs) + 1
    $bins = New-Object object[] $binCount
    for ($i = 0; $i -lt $binCount; $i++) {
        $bins[$i] = New-EmptyBin
    }

    foreach ($event in $Events) {
        $relativeNs = [int64]$event.TimestampNs - $TraceStartNs
        $binIndex = [int][Math]::Floor(([double]$relativeNs) / $binNs)
        if ($binIndex -lt 0 -or $binIndex -ge $bins.Count) {
            continue
        }

        $bin = $bins[$binIndex]
        $bin.total++
        if ($event.EventClass -eq 'LINK_CMD') {
            $bin.link_cmd++
        }
        elseif ($event.EventClass -eq 'LTSSM_STATE') {
            $bin.ltssm_state++
        }
        elseif ($event.EventClass -eq 'LFPS') {
            $bin.lfps++
            $signature = Get-LfpsRawSignature -Event $event
            if ($null -ne $signature -and
                $PassGlobalCounts.ContainsKey($signature) -and
                [int64]$PassGlobalCounts[$signature] -le $rarePassGlobalCountThreshold) {
                $bin.rare_lfps++
            }
            elseif ($null -ne $signature -and
                -not $PassGlobalCounts.ContainsKey($signature)) {
                $bin.rare_lfps++
            }
        }
    }

    return ,$bins
}

function Get-WindowFeatures {
    param(
        [object[]] $Bins,
        [int] $StartBin,
        [int] $WindowBinCount,
        [int64] $TraceStartNs
    )

    $link = [int64]0
    $ltssm = [int64]0
    $lfps = [int64]0
    $total = [int64]0
    $rare = [int64]0
    $endBin = [Math]::Min($Bins.Count - 1, $StartBin + $WindowBinCount - 1)
    for ($i = $StartBin; $i -le $endBin; $i++) {
        $link += $Bins[$i].link_cmd
        $ltssm += $Bins[$i].ltssm_state
        $lfps += $Bins[$i].lfps
        $total += $Bins[$i].total
        $rare += $Bins[$i].rare_lfps
    }

    $startNs = $TraceStartNs + ([int64]$StartBin * $strideNs)
    return [ordered]@{
        start_bin = $StartBin
        start_timestamp_ns = $startNs
        end_timestamp_ns = $startNs + $windowNs
        link_cmd_count = $link
        ltssm_state_count = $ltssm
        lfps_count = $lfps
        total_count = $total
        rare_lfps_count = $rare
        lfps_ratio = if ($total -gt 0) { [double]$lfps / [double]$total } else { 0.0 }
    }
}

function Get-FeatureValues {
    param([object[]] $Windows, [string] $Property)

    $values = [System.Collections.Generic.List[double]]::new()
    foreach ($window in $Windows) {
        $values.Add([double]$window[$Property])
    }
    return ,$values.ToArray()
}

function Get-Percentile {
    param([double[]] $Values, [double] $Percentile)

    if ($Values.Count -eq 0) {
        return 0.0
    }
    $sorted = @($Values | Sort-Object)
    $position = ($sorted.Count - 1) * $Percentile
    $lower = [int][Math]::Floor($position)
    $upper = [int][Math]::Ceiling($position)
    if ($lower -eq $upper) {
        return [double]$sorted[$lower]
    }
    $fraction = $position - $lower
    return ([double]$sorted[$lower] +
        (($sorted[$upper] - $sorted[$lower]) * $fraction))
}

function Get-BaselineStats {
    param([object[]] $Windows)

    $stats = [ordered]@{}
    foreach ($property in @('lfps_count', 'ltssm_state_count', 'link_cmd_count', 'lfps_ratio', 'rare_lfps_count')) {
        $values = Get-FeatureValues -Windows $Windows -Property $property
        $stats[$property] = [ordered]@{
            median = Get-Percentile -Values $values -Percentile 0.50
            p95 = Get-Percentile -Values $values -Percentile 0.95
            max = Get-Percentile -Values $values -Percentile 1.0
        }
    }
    return $stats
}

function Get-HighValueScore {
    param(
        [double] $Value,
        $Stats
    )

    $p95 = [double]$Stats.p95
    if ($Value -le 0) {
        return 0.0
    }
    if ($p95 -le 0) {
        # Avoid turning a single event into a saturated anomaly when the
        # baseline percentile is zero. Larger bursts still approach 1.
        return [Math]::Min(1.0, $Value / ($Value + 10.0))
    }
    if ($Value -le $p95) {
        return [Math]::Min(0.25, $Value / (($p95 * 4.0) + 1.0))
    }
    return [Math]::Min(
        1.0,
        0.25 + (0.75 * (($Value - $p95) / ($Value + $p95 + 1.0))))
}

function Get-LowValueScore {
    param(
        [double] $Value,
        $Stats
    )

    $median = [double]$Stats.median
    if ($median -le 0 -or $Value -ge $median) {
        return 0.0
    }
    return [Math]::Min(1.0, ($median - $Value) / ($median + 1.0))
}

function Add-ScoreAndReasons {
    param($Window, $Stats)

    $lfpsScore = Get-HighValueScore -Value $Window.lfps_count -Stats $Stats.lfps_count
    $rareScore = Get-HighValueScore -Value $Window.rare_lfps_count -Stats $Stats.rare_lfps_count
    $ltssmScore = Get-HighValueScore -Value $Window.ltssm_state_count -Stats $Stats.ltssm_state_count
    $linkDeficitScore = Get-LowValueScore -Value $Window.link_cmd_count -Stats $Stats.link_cmd_count
    $ratioScore = Get-HighValueScore -Value $Window.lfps_ratio -Stats $Stats.lfps_ratio
    $score = (0.45 * $lfpsScore) +
        (0.25 * $rareScore) +
        (0.15 * $ltssmScore) +
        (0.10 * $linkDeficitScore) +
        (0.05 * $ratioScore)

    $reasons = [System.Collections.Generic.List[string]]::new()
    if ($lfpsScore -gt 0.25) { $reasons.Add('LFPS burst above PASS baseline') }
    if ($rareScore -gt 0.25) { $reasons.Add('rare/unseen raw LFPS signatures') }
    if ($ltssmScore -gt 0.25) { $reasons.Add('LTSSM density above PASS baseline') }
    if ($linkDeficitScore -gt 0.25) { $reasons.Add('LINK_CMD activity below PASS baseline') }
    if ($ratioScore -gt 0.25) { $reasons.Add('LFPS share of events above PASS baseline') }

    $Window['score'] = [Math]::Round($score, 6)
    $Window['reasons'] = @($reasons.ToArray())
    return $Window
}

function Get-TopRawSignatures {
    param(
        [object[]] $Events,
        [int64] $StartNs,
        [int64] $EndNs
    )

    $counts = @{}
    foreach ($event in $Events) {
        if ($event.EventClass -ne 'LFPS' -or
            [int64]$event.TimestampNs -lt $StartNs -or
            [int64]$event.TimestampNs -ge $EndNs) {
            continue
        }
        $signature = Get-LfpsRawSignature -Event $event
        if ($null -eq $signature) { continue }
        if ($counts.ContainsKey($signature)) { $counts[$signature]++ }
        else { $counts[$signature] = [int64]1 }
    }

    $top = [System.Collections.Generic.List[object]]::new()
    foreach ($entry in ($counts.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5)) {
        $parts = $entry.Key.Split('|')
        $top.Add([ordered]@{
            lfps_type = [int64]$parts[0]
            pattern_type = [int64]$parts[1]
            duration_ns = [int64]$parts[2]
            starts_pattern = [int64]$parts[3]
            count = [int64]$entry.Value
        })
    }
    return @($top.ToArray())
}

function Select-NonOverlappingTopRegions {
    param([object[]] $Windows, [int] $Limit)

    $selected = [System.Collections.Generic.List[object]]::new()
    foreach ($window in @($Windows | Sort-Object @{Expression = { [double]$_.score }; Descending = $true})) {
        $overlaps = $false
        foreach ($existing in $selected) {
            if ([int64]$window.start_timestamp_ns -lt [int64]$existing.end_timestamp_ns -and
                [int64]$window.end_timestamp_ns -gt [int64]$existing.start_timestamp_ns) {
                $overlaps = $true
                break
            }
        }
        if ($overlaps) { continue }
        $selected.Add($window)
        if ($selected.Count -ge $Limit) { break }
    }
    return @($selected.ToArray())
}

function Get-TraceOverview {
    param($Timeline)

    return [ordered]@{
        total_events = [int64]$Timeline.target_event_count
        link_cmd = [int64]$Timeline.declared_link_cmd_count
        ltssm_state = [int64]$Timeline.declared_ltssm_count
        lfps = [int64]$Timeline.declared_lfps_count
    }
}

Assert-TimelineInput -Timeline $pass -Events $passEvents -Name 'PASS'
Assert-TimelineInput -Timeline $fail -Events $failEvents -Name 'FAIL'

$passStartNs = Get-TraceStartNs -Events $passEvents
$passEndNs = Get-TraceEndNs -Events $passEvents
$failStartNs = Get-TraceStartNs -Events $failEvents
$failEndNs = Get-TraceEndNs -Events $failEvents
$passGlobalCounts = Get-GlobalLfpsCounts -Events $passEvents
$passBins = Build-Bins -Events $passEvents -TraceStartNs $passStartNs -TraceEndNs $passEndNs -PassGlobalCounts $passGlobalCounts
$failBins = Build-Bins -Events $failEvents -TraceStartNs $failStartNs -TraceEndNs $failEndNs -PassGlobalCounts $passGlobalCounts
$windowBinCount = [int]($windowNs / $binNs)
$passWindowCount = [Math]::Max(1, [int][Math]::Ceiling(([double]$passBins.Count - $windowBinCount + 1) * $binNs / $strideNs))
$failWindowCount = [Math]::Max(1, [int][Math]::Ceiling(([double]$failBins.Count - $windowBinCount + 1) * $binNs / $strideNs))

$passWindows = [System.Collections.Generic.List[object]]::new()
for ($i = 0; $i -lt $passWindowCount; $i++) {
    $passWindows.Add((Get-WindowFeatures -Bins $passBins -StartBin $i -WindowBinCount $windowBinCount -TraceStartNs $passStartNs))
}
$failWindows = [System.Collections.Generic.List[object]]::new()
for ($i = 0; $i -lt $failWindowCount; $i++) {
    $failWindows.Add((Get-WindowFeatures -Bins $failBins -StartBin $i -WindowBinCount $windowBinCount -TraceStartNs $failStartNs))
}

$baselineStats = Get-BaselineStats -Windows $passWindows.ToArray()
$scoredFailWindows = [System.Collections.Generic.List[object]]::new()
foreach ($window in $failWindows) {
    $scoredFailWindows.Add((Add-ScoreAndReasons -Window $window -Stats $baselineStats))
}

$selectedWindows = Select-NonOverlappingTopRegions -Windows $scoredFailWindows.ToArray() -Limit $TopK
$candidates = [System.Collections.Generic.List[object]]::new()
$rank = 1
foreach ($window in $selectedWindows) {
    $candidates.Add([ordered]@{
        rank = $rank
        score = $window.score
        start_timestamp_ns = $window.start_timestamp_ns
        end_timestamp_ns = $window.end_timestamp_ns
        link_cmd_count = $window.link_cmd_count
        ltssm_state_count = $window.ltssm_state_count
        lfps_count = $window.lfps_count
        total_count = $window.total_count
        rare_lfps_count = $window.rare_lfps_count
        lfps_ratio = $window.lfps_ratio
        reasons = $window.reasons
        top_raw_lfps_signatures = Get-TopRawSignatures `
            -Events $failEvents `
            -StartNs $window.start_timestamp_ns `
            -EndNs $window.end_timestamp_ns
    })
    $rank++
}

$artifact = [ordered]@{
    analysis = 'C5 automatic suspicious-region discovery'
    pass_timeline = $PassTimelinePath
    fail_timeline = $FailTimelinePath
    status = 'PASS'
    top_k = $TopK
    trace_relative_windows = $true
    absolute_cross_trace_alignment_used = $false
    windowing = [ordered]@{
        window_ns = $windowNs
        stride_ns = $strideNs
        bin_ns = $binNs
        rare_pass_global_count_threshold = $rarePassGlobalCountThreshold
    }
    pass_overview = Get-TraceOverview -Timeline $pass
    fail_overview = Get-TraceOverview -Timeline $fail
    pass_baseline = [ordered]@{
        start_timestamp_ns = $passStartNs
        end_timestamp_ns = $passEndNs
        window_count = $passWindows.Count
        feature_stats = $baselineStats
    }
    fail_scan = [ordered]@{
        start_timestamp_ns = $failStartNs
        end_timestamp_ns = $failEndNs
        window_count = $failWindows.Count
    }
    candidates = @($candidates.ToArray())
    claims = @(
        'The FAIL candidates are ranked without an engineer-supplied timestamp, event index, or root-cause hint.',
        'PASS is used as a behavioral baseline; windows are relative to each trace and are not cross-trace timestamp alignment.',
        'Raw LFPS values are reported numerically and are not assigned enum names.',
        'Candidate ranking is triage evidence, not root cause, severity, or automatic PASS/FAIL classification.',
        'The ground-truth region is not an input to this analysis; it is reserved for post-run qualification.'
    )
    trace_integrity_qualified = (
        $pass.trace_integrity_unchanged -eq $true -and
        $fail.trace_integrity_unchanged -eq $true
    )
}

[System.IO.File]::WriteAllText(
    $OutputPath,
    (($artifact | ConvertTo-Json -Depth 20) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false))

$readBack = Get-Content -LiteralPath $OutputPath -Raw | ConvertFrom-Json
if ($readBack.status -ne 'PASS' -or $readBack.candidates.Count -gt $TopK) {
    throw 'C5 suspicious-region JSON read-back verification failed.'
}

[pscustomobject]@{
    output_path = $OutputPath
    status = $readBack.status
    top_k = $readBack.top_k
    candidate_count = $readBack.candidates.Count
    top_candidate = if ($readBack.candidates.Count -gt 0) {
        ($readBack.candidates[0] | ConvertTo-Json -Compress -Depth 8)
    }
    else { '{}' }
    trace_integrity_qualified = $readBack.trace_integrity_qualified
} | ConvertTo-Json -Compress
