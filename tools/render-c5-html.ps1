param(
    [Parameter(Mandatory = $true)]
    [string] $InputPath,

    [Parameter(Mandatory = $true)]
    [string] $OutputPath
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
    throw "C5 JSON does not exist: $InputPath"
}
if (Test-Path -LiteralPath $OutputPath) {
    throw "Refusing to overwrite existing output: $OutputPath"
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory -and -not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$data = Get-Content -LiteralPath $InputPath -Raw | ConvertFrom-Json
if ($data.status -ne 'PASS') {
    throw "Only a passing C5 artifact can be rendered: $($data.status)"
}
if ($null -eq $data.pass_overview -or $null -eq $data.fail_overview) {
    throw 'C5 JSON does not contain PASS/FAIL overview fields. Re-run C5 with the current scorer.'
}

function HtmlEncode {
    param([AllowNull()][object] $Value)

    return [System.Net.WebUtility]::HtmlEncode([string]$Value)
}

function Format-Ns {
    param([int64] $Nanoseconds)

    $seconds = [int64][Math]::Floor(([double]$Nanoseconds) / 1000000000.0)
    $remainder = $Nanoseconds - ($seconds * 1000000000L)
    return ('{0}.{1:D9} sec' -f $seconds, $remainder)
}

function Format-Count {
    param([int64] $Value)

    return $Value.ToString('N0', [Globalization.CultureInfo]::InvariantCulture)
}

function Format-Percent {
    param([double] $Value)

    return $Value.ToString('P1', [Globalization.CultureInfo]::InvariantCulture)
}

function Get-OverviewValue {
    param($Overview, [string] $Property)

    $propertyInfo = $Overview.PSObject.Properties[$Property]
    if ($null -eq $propertyInfo) { return 0 }
    return [int64]$propertyInfo.Value
}

function Get-BaselineValue {
    param($FeatureStats, [string] $Property, [string] $Statistic = 'p95')

    $feature = $FeatureStats.PSObject.Properties[$Property]
    if ($null -eq $feature) { return 0.0 }
    $stat = $feature.Value.PSObject.Properties[$Statistic]
    if ($null -eq $stat) { return 0.0 }
    return [double]$stat.Value
}

function Get-LocalizedReason {
    param([string] $Reason)

    switch ($Reason) {
        'LFPS burst above PASS baseline' {
            return '&#36899;&#32218;&#35338;&#34399;&#65288;LFPS&#65289;&#27604;&#27491;&#24120;&#32000;&#37636;&#22810;&#12290;'
        }
        'rare/unseen raw LFPS signatures' {
            return '&#20986;&#29694;&#27491;&#24120;&#32000;&#37636;&#24456;&#23569;&#35211;&#12289;&#29978;&#33267;&#27794;&#20986;&#29694;&#36942;&#30340;&#36899;&#32218;&#35338;&#34399;&#29305;&#24501;&#65288;LFPS&#65289;&#12290;'
        }
        'LTSSM density above PASS baseline' {
            return '&#36899;&#32218;&#29376;&#24907;&#35722;&#21270;&#65288;LTSSM&#65289;&#27604;&#27491;&#24120;&#32000;&#37636;&#38971;&#32321;&#12290;'
        }
        'LINK_CMD activity below PASS baseline' {
            return 'LINK_CMD &#21629;&#20196;&#27604;&#27491;&#24120;&#32000;&#37636;&#23569;&#12290;'
        }
        default {
            return HtmlEncode $Reason
        }
    }
}

function Get-LocalizedClaim {
    param([string] $Claim)

    switch ($Claim) {
        'The FAIL candidates are ranked without an engineer-supplied timestamp, event index, or root-cause hint.' {
            return '&#27794;&#26377;&#20107;&#20808;&#21578;&#35380;&#24037;&#20855;&#25925;&#38556;&#26178;&#38291;&#65292;&#24037;&#20855;&#20173;&#21487;&#33258;&#21205;&#25214;&#20986;&#20540;&#24471;&#20808;&#26597;&#30475;&#30340;&#21312;&#27573;&#12290;'
        }
        'PASS is used as a behavioral baseline; windows are relative to each trace and are not cross-trace timestamp alignment.' {
            return '&#27491;&#24120; PASS &#32000;&#37636;&#29992;&#20358;&#27604;&#36611;&#21508;&#33258; trace &#30340;&#26178;&#38291;&#21312;&#27573;&#65292;&#19981;&#26159;&#25226;&#20841;&#20221; trace &#30340;&#32085;&#23565;&#26178;&#38291;&#24375;&#34892;&#23565;&#40778;&#12290;'
        }
        'Raw LFPS values are reported numerically and are not assigned enum names.' {
            return '&#21407;&#22987; LFPS &#20540;&#20197;&#25976;&#20540;&#26684;&#24335;&#21576;&#29694;&#65292;&#19981;&#33258;&#34892;&#25351;&#23450; enum &#21517;&#31281;&#12290;'
        }
        'Candidate ranking is triage evidence, not root cause, severity, or automatic PASS/FAIL classification.' {
            return '&#25490;&#21517;&#21482;&#33021;&#21578;&#35380;&#20320;&#21738;&#20123;&#21312;&#27573;&#20540;&#24471;&#20808;&#30475;&#65292;&#19981;&#33021;&#21028;&#23450;&#30495;&#27491;&#25925;&#38556;&#21407;&#22240;&#12289;&#22196;&#37325;&#24230;&#25110;&#29986;&#21697; PASS/FAIL&#12290;'
        }
        'The ground-truth region is not an input to this analysis; it is reserved for post-run qualification.' {
            return '&#24037;&#31243;&#24107;&#27161;&#35352;&#30340;&#27491;&#30906;&#21312;&#22495;&#19981;&#26159;&#20998;&#26512;&#36664;&#20837;&#65292;&#20677;&#29992;&#26044;&#23436;&#25104;&#24460;&#30340; qualification &#39511;&#35657;&#12290;'
        }
        default {
            return HtmlEncode $Claim
        }
    }
}

function Get-DeltaText {
    param([string] $Metric, [double] $Value, [double] $Baseline)

    if ($Metric -eq 'LINK_CMD') {
        if ($Value -lt $Baseline) { return '&#8595; &#26126;&#39023;&#20559;&#23569;' }
        if ($Value -gt $Baseline) { return '&#8593; &#24456;&#19981;&#23563;&#24120;' }
        return '&#25509;&#36817;&#27491;&#24120;'
    }
    if ($Value -gt $Baseline) { return '&#8593; &#24456;&#19981;&#23563;&#24120;' }
    if ($Value -lt $Baseline) { return '&#8595; &#26126;&#39023;&#20559;&#23569;' }
    return '&#25509;&#36817;&#27491;&#24120;'
}

function New-Episode {
    param([object[]] $Windows)

    $start = [int64]::MaxValue
    $end = [int64]::MinValue
    [int64]$lfps = 0
    [int64]$ltssm = 0
    [int64]$link = 0
    [int64]$total = 0
    [int64]$rare = 0
    [double]$score = 0.0
    [int]$primaryRank = [int]::MaxValue
    $reasons = @()
    $rawSignatures = @()

    foreach ($window in $Windows) {
        $windowStart = [int64]$window.start_timestamp_ns
        $windowEnd = [int64]$window.end_timestamp_ns
        $start = [Math]::Min($start, $windowStart)
        $end = [Math]::Max($end, $windowEnd)
        $lfps += [int64]$window.lfps_count
        $ltssm += [int64]$window.ltssm_state_count
        $link += [int64]$window.link_cmd_count
        $total += [int64]$window.total_count
        $rare += [int64]$window.rare_lfps_count
        $score = [Math]::Max($score, [double]$window.score)
        $primaryRank = [Math]::Min($primaryRank, [int]$window.rank)
        $reasons += @($window.reasons)
        $rawSignatures += @($window.top_raw_lfps_signatures)
    }

    $uniqueReasons = @($reasons | Select-Object -Unique)
    $durationNs = $end - $start
    $ratio = if ($total -gt 0) { [double]$lfps / [double]$total } else { 0.0 }

    return [pscustomobject]@{
        primary_rank = $primaryRank
        start_timestamp_ns = $start
        end_timestamp_ns = $end
        duration_ns = $durationNs
        lfps_count = $lfps
        ltssm_state_count = $ltssm
        link_cmd_count = $link
        total_count = $total
        rare_lfps_count = $rare
        lfps_ratio = $ratio
        score = $score
        windows = @($Windows)
        reasons = $uniqueReasons
        raw_signatures = @($rawSignatures | Select-Object -First 8)
    }
}

function Add-Metric {
    param(
        [System.Text.StringBuilder] $Builder,
        [string] $Label,
        [string] $Value
    )

    $safeLabel = if ($Label -match '&#') { $Label } else { HtmlEncode $Label }
    $Builder.AppendLine(("<div class='timeline-stat'><span>{0}</span><strong>{1}</strong></div>" -f
        $safeLabel, (HtmlEncode $Value))) | Out-Null
}

function Format-ShortTime {
    param([int64] $Nanoseconds)

    return ('{0:F3} sec' -f (([double]$Nanoseconds) / 1000000000.0))
}

function Resolve-ReferencePath {
    param(
        [string] $ReferencePath,
        [string] $ArtifactPath
    )

    $artifactDirectory = Split-Path -Parent ([string](Resolve-Path -LiteralPath $ArtifactPath))
    $candidates = @(
        $ReferencePath,
        (Join-Path $artifactDirectory $ReferencePath),
        (Join-Path (Get-Location) $ReferencePath)
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return ([string](Resolve-Path -LiteralPath $candidate))
        }
    }
    return $null
}

function Load-ReferencedTimeline {
    param(
        [string] $ReferencePath,
        [string] $ArtifactPath
    )

    $resolved = Resolve-ReferencePath -ReferencePath $ReferencePath -ArtifactPath $ArtifactPath
    if ($null -eq $resolved) { return $null }
    try {
        return (Get-Content -LiteralPath $resolved -Raw | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

function New-EvidenceTimelineSvg {
    param(
        [object[]] $Events,
        [int64] $StartNs,
        [int64] $EndNs
    )

    if ($null -eq $Events -or $Events.Count -eq 0 -or $EndNs -le $StartNs) {
        return $null
    }

    $width = 1000
    $height = 205
    $left = 145
    $right = 20
    $plotWidth = $width - $left - $right
    $duration = [double]($EndNs - $StartNs)
    $svg = [System.Text.StringBuilder]::new()
    $svg.AppendLine(("<svg class='evidence-svg' viewBox='0 0 {0} {1}' role='img' aria-label='Protocol event timeline'>" -f $width, $height)) | Out-Null
    $svg.AppendLine("<line x1='$left' y1='24' x2='$($left + $plotWidth)' y2='24' stroke='#2b3b4c' stroke-width='1'/>") | Out-Null
    $svg.AppendLine(("<text x='$left' y='16' fill='#9fb0c0' font-size='12'>{0}</text>" -f (HtmlEncode (Format-Ns $StartNs)))) | Out-Null
    $midNs = [int64]($StartNs + (($EndNs - $StartNs) / 2))
    $midX = $left + ($plotWidth / 2)
    $svg.AppendLine(("<text x='{0:N1}' y='16' text-anchor='middle' fill='#9fb0c0' font-size='12'>{1}</text>" -f $midX, (HtmlEncode (Format-Ns $midNs)))) | Out-Null
    $svg.AppendLine(("<text x='{0}' y='16' text-anchor='end' fill='#9fb0c0' font-size='12'>{1}</text>" -f ($left + $plotWidth), (HtmlEncode (Format-Ns $EndNs)))) | Out-Null

    $rows = @(
        [pscustomobject]@{ name = '&#36899;&#32218;&#35338;&#34399;&#65288;LFPS&#65289;&#23494;&#24230;'; key = 'LFPS'; y = 62 },
        [pscustomobject]@{ name = '&#36899;&#32218;&#29376;&#24907;&#65288;LTSSM&#65289;'; key = 'LTSSM_STATE'; y = 112 },
        [pscustomobject]@{ name = 'LINK_CMD &#21629;&#20196;'; key = 'LINK_CMD'; y = 162 }
    )
    foreach ($row in $rows) {
        $svg.AppendLine(("<text x='10' y='{0}' fill='#edf4fa' font-size='13'>{1}</text><line x1='$left' y1='{0}' x2='$($left + $plotWidth)' y2='{0}' stroke='#253342' stroke-width='8' stroke-linecap='round'/>" -f $row.y, $row.name)) | Out-Null
    }

    $lfpsEvents = @($Events | Where-Object { $_.EventClass -eq 'LFPS' })
    $ltssmEvents = @($Events | Where-Object { $_.EventClass -eq 'LTSSM_STATE' })
    $linkEvents = @($Events | Where-Object { $_.EventClass -eq 'LINK_CMD' })
    $sortedLtssmEvents = @($ltssmEvents | Sort-Object @{Expression = { [int64]$_.TimestampNs }})
    $importantLtssmIndexes = @()
    if ($sortedLtssmEvents.Count -gt 0) {
        $importantLtssmIndexes += 0
        if ($sortedLtssmEvents.Count -gt 2) {
            $largestGap = [int64]::MinValue
            $largestGapIndex = 0
            for ($gapIndex = 0; $gapIndex -lt ($sortedLtssmEvents.Count - 1); $gapIndex++) {
                $gap = [int64]$sortedLtssmEvents[$gapIndex + 1].TimestampNs - [int64]$sortedLtssmEvents[$gapIndex].TimestampNs
                if ($gap -gt $largestGap) {
                    $largestGap = $gap
                    $largestGapIndex = $gapIndex
                }
            }
            $importantLtssmIndexes += $largestGapIndex
        }
        $importantLtssmIndexes += ($sortedLtssmEvents.Count - 1)
        $importantLtssmIndexes = @($importantLtssmIndexes | Select-Object -Unique | Sort-Object)
    }
    $binCount = 160
    $bins = New-Object 'int[]' $binCount
    foreach ($event in $lfpsEvents) {
        $fraction = ([double]([int64]$event.TimestampNs - $StartNs)) / $duration
        $bin = [Math]::Min($binCount - 1, [Math]::Max(0, [int][Math]::Floor($fraction * $binCount)))
        $bins[$bin]++
    }
    $maxBin = 1
    foreach ($binValue in $bins) { $maxBin = [Math]::Max($maxBin, $binValue) }
    for ($i = 0; $i -lt $binCount; $i++) {
        if ($bins[$i] -eq 0) { continue }
        $x = $left + (($i / [double]$binCount) * $plotWidth)
        $barWidth = [Math]::Max(1.0, ($plotWidth / $binCount) - 0.8)
        $barHeight = 6.0 + (([double]$bins[$i] / $maxBin) * 14.0)
        $y = 62 - ($barHeight / 2)
        $svg.AppendLine(("<rect x='{0:N2}' y='{1:N2}' width='{2:N2}' height='{3:N2}' rx='1' fill='#58A6FF' opacity='0.9'><title>LFPS density bin: {4}</title></rect>" -f $x, $y, $barWidth, $barHeight, $bins[$i])) | Out-Null
    }

    for ($ltssmIndex = 0; $ltssmIndex -lt $sortedLtssmEvents.Count; $ltssmIndex++) {
        $event = $sortedLtssmEvents[$ltssmIndex]
        $fraction = ([double]([int64]$event.TimestampNs - $StartNs)) / $duration
        $x = $left + ($fraction * $plotWidth)
        $svg.AppendLine(("<circle cx='{0:N2}' cy='112' r='5' fill='#F0A33A'><title>LTSSM event at {1}</title></circle>" -f $x, (HtmlEncode (Format-Ns ([int64]$event.TimestampNs))))) | Out-Null
        if ($importantLtssmIndexes -contains $ltssmIndex) {
            $svg.AppendLine(("<text x='{0:N2}' y='94' text-anchor='middle' fill='#F0A33A' font-size='11'>{1}</text>" -f $x, (HtmlEncode (Format-Ns ([int64]$event.TimestampNs))))) | Out-Null
        }
    }
    foreach ($event in $linkEvents) {
        $fraction = ([double]([int64]$event.TimestampNs - $StartNs)) / $duration
        $x = $left + ($fraction * $plotWidth)
        $svg.AppendLine(("<circle cx='{0:N2}' cy='162' r='4' fill='#8B949E'><title>LINK_CMD event at {1}</title></circle>" -f $x, (HtmlEncode (Format-Ns ([int64]$event.TimestampNs))))) | Out-Null
    }
    if ($linkEvents.Count -eq 0) {
        $svg.AppendLine(("<text x='{0:N1}' y='166' text-anchor='middle' fill='#9fb0c0' font-size='12'>&#36889;&#27573;&#27794;&#26377;&#35264;&#23519;&#21040; LINK_CMD</text>" -f ($left + ($plotWidth / 2)))) | Out-Null
    }
    $svg.AppendLine('</svg>') | Out-Null
    return $svg.ToString()
}

$passName = Split-Path -Leaf ([string]$data.pass_timeline)
$failName = Split-Path -Leaf ([string]$data.fail_timeline)
$candidateList = @($data.candidates | Sort-Object @{Expression = { [int64]$_.start_timestamp_ns }})

$episodeList = @()
$currentWindows = @()
[int64]$currentEnd = [int64]::MinValue
foreach ($candidate in $candidateList) {
    $candidateStart = [int64]$candidate.start_timestamp_ns
    if ($currentWindows.Count -eq 0 -or $candidateStart -le $currentEnd) {
        $currentWindows += $candidate
        $currentEnd = [Math]::Max($currentEnd, [int64]$candidate.end_timestamp_ns)
    }
    else {
        $episodeList += ,(New-Episode -Windows $currentWindows)
        $currentWindows = @($candidate)
        $currentEnd = [int64]$candidate.end_timestamp_ns
    }
}
if ($currentWindows.Count -gt 0) {
    $episodeList += ,(New-Episode -Windows $currentWindows)
}
$episodes = @($episodeList | Sort-Object @{Expression = { [int]$_.primary_rank }})
$primaryEpisode = if ($episodes.Count -gt 0) { $episodes[0] } else { $null }
$baselineStats = $data.pass_baseline.feature_stats
$failTimeline = Load-ReferencedTimeline -ReferencePath ([string]$data.fail_timeline) -ArtifactPath $InputPath
$passTimeline = Load-ReferencedTimeline -ReferencePath ([string]$data.pass_timeline) -ArtifactPath $InputPath
$failTraceName = if ($null -ne $failTimeline -and $failTimeline.trace) { Split-Path -Leaf ([string]$failTimeline.trace) } else { $failName }
$passTraceName = if ($null -ne $passTimeline -and $passTimeline.trace) { Split-Path -Leaf ([string]$passTimeline.trace) } else { $passName }
$localEvents = @()
$timelineSvg = $null
if ($null -ne $primaryEpisode -and $null -ne $failTimeline -and $failTimeline.events) {
    $localEvents = @($failTimeline.events | Where-Object {
        [int64]$_.TimestampNs -ge [int64]$primaryEpisode.start_timestamp_ns -and
        [int64]$_.TimestampNs -le [int64]$primaryEpisode.end_timestamp_ns
    })
    $timelineSvg = New-EvidenceTimelineSvg -Events $localEvents -StartNs ([int64]$primaryEpisode.start_timestamp_ns) -EndNs ([int64]$primaryEpisode.end_timestamp_ns)
}

$html = [System.Text.StringBuilder]::new()
$html.AppendLine('<!doctype html>') | Out-Null
$html.AppendLine('<html lang="zh-Hant"><head><meta charset="utf-8">') | Out-Null
$html.AppendLine('<meta name="viewport" content="width=device-width, initial-scale=1">') | Out-Null
$html.AppendLine('<title>LeCroy Trace &#21021;&#27493;&#20998;&#26512;</title>') | Out-Null
$html.AppendLine(@'
<style>
:root { color-scheme:dark; --bg:#0D1117; --panel:#161B22; --panel-2:#1C232D; --line:#30363D; --text:#F0F3F6; --muted:#8B949E; --accent:#58A6FF; --warn:#F0A33A; --success:#3FB950; --danger:#F47067; --blue:#58A6FF; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:15px/1.55 "Segoe UI", "Microsoft JhengHei", system-ui, sans-serif; }
a { color:var(--blue); }
a:focus-visible, summary:focus-visible { outline:2px solid var(--accent); outline-offset:3px; }
.shell { max-width:1040px; margin:0 auto; padding:32px 22px 64px; }
.eyebrow { color:var(--accent); font-size:12px; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
h1 { margin:6px 0 4px; font-size:clamp(28px,5vw,46px); line-height:1.08; }
h2 { margin:0 0 16px; font-size:22px; }
h3 { margin:0; font-size:18px; }
p { color:var(--muted); }
.hero, .panel, .episode { background:var(--panel); border:1px solid var(--line); border-radius:16px; }
.hero { padding:28px; display:grid; gap:22px; }
.hero-label { color:var(--muted); margin:0; }
.state-line { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:18px; }
.badge { color:#251A05; background:var(--warn); border-radius:999px; padding:5px 10px; font-size:12px; font-weight:800; letter-spacing:.05em; }
.boundary { color:var(--warn); font-weight:650; }
.priority-label { margin:0; color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.08em; }
.priority-time { margin:7px 0 0; color:var(--text); font:650 clamp(25px,4vw,42px)/1.1 ui-monospace, SFMono-Regular, Consolas, monospace; }
.priority-meta { color:var(--muted); font:13px ui-monospace, SFMono-Regular, Consolas, monospace; margin-top:10px; }
.action { border-left:3px solid var(--warn); padding:12px 14px; background:rgba(240,163,58,.08); }
.action strong { color:var(--text); }
.observation-summary { border-left:3px solid var(--blue); padding:12px 14px; background:rgba(88,166,255,.08); }
.observation-summary strong { color:var(--text); }
.observation-summary p { margin:6px 0 0; color:var(--text); }
.observe { border-top:1px solid var(--line); padding-top:18px; }
.observe ul, .reasons { margin:10px 0 0; padding-left:22px; color:var(--muted); }
.observe li + li, .reasons li + li { margin-top:4px; }
.section { margin-top:28px; }
.panel { padding:22px; }
.comparison table { margin-top:8px; }
table { width:100%; border-collapse:collapse; }
th, td { border-bottom:1px solid var(--line); padding:11px 10px; text-align:right; vertical-align:top; }
th:first-child, td:first-child { text-align:left; }
th { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
.comparison td:last-child { color:var(--warn); }
.small { color:var(--muted); font-size:13px; }
.timeline-scale { display:flex; justify-content:space-between; gap:12px; color:var(--muted); font:13px ui-monospace, SFMono-Regular, Consolas, monospace; }
.timeline-rail { height:14px; margin:12px 0 18px; padding:3px; background:#253342; border-radius:99px; }
.timeline-range { display:block; height:100%; width:100%; background:var(--warn); border-radius:99px; }
.timeline-stats { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.timeline-stat { background:var(--panel-2); border-radius:10px; padding:12px; }
.timeline-stat span { display:block; color:var(--muted); font-size:12px; }
.timeline-stat strong { display:block; margin-top:3px; font:650 19px ui-monospace, SFMono-Regular, Consolas, monospace; }
.evidence-svg { display:block; width:100%; height:auto; min-height:205px; background:#0a0f15; border:1px solid var(--line); border-radius:10px; }
.other-list { display:grid; gap:10px; }
.other-episode { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:15px 17px; }
.other-head { display:flex; justify-content:space-between; gap:12px; align-items:baseline; }
.other-time { color:var(--text); font:14px ui-monospace, SFMono-Regular, Consolas, monospace; margin-top:6px; }
.rank-score { color:var(--muted); font:13px ui-monospace, SFMono-Regular, Consolas, monospace; white-space:nowrap; }
.details-grid { display:grid; gap:12px; }
details { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px 18px; }
summary { cursor:pointer; color:var(--text); font-weight:650; }
details[open] summary { margin-bottom:14px; }
.raw-table { overflow:auto; }
.warning { color:var(--warn); }
.status { color:var(--success); font-weight:700; }
footer { margin-top:30px; color:var(--muted); font-size:12px; }
@media (max-width:700px) { .shell { padding:22px 14px 44px; } .hero, .panel, .episode { border-radius:12px; padding:18px; } .timeline-stats { grid-template-columns:1fr; } .other-head { align-items:flex-start; flex-direction:column; gap:5px; } }
@media (prefers-reduced-motion:reduce) { *, *::before, *::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; } }
</style>
'@) | Out-Null
$html.AppendLine('</head><body><main class="shell">') | Out-Null

$html.AppendLine('<section class="hero" aria-labelledby="page-title">') | Out-Null
$html.AppendLine('<div><div class="eyebrow">FAIL TRACE &#21021;&#27493;&#20998;&#26512;</div><h1 id="page-title">LeCroy Trace &#21021;&#27493;&#20998;&#26512;</h1>') | Out-Null
$html.AppendLine(("<p class='hero-label'>FAIL trace&#65306;<code>{0}</code><br>&#27491;&#24120; PASS &#32000;&#37636;&#65306;<code>{1}</code></p>" -f (HtmlEncode $failTraceName), (HtmlEncode $passTraceName))) | Out-Null
$html.AppendLine('<div class="state-line"><span class="badge">&#20540;&#24471;&#20778;&#20808;&#27298;&#26597;&#30340;&#21312;&#27573;</span><span class="boundary">&#23578;&#26410;&#30906;&#35469;&#30495;&#27491;&#21407;&#22240;</span></div></div>') | Out-Null
if ($null -ne $primaryEpisode) {
    $primaryStart = Format-Ns ([int64]$primaryEpisode.start_timestamp_ns)
    $primaryEnd = Format-Ns ([int64]$primaryEpisode.end_timestamp_ns)
    $durationMs = ([double]$primaryEpisode.duration_ns / 1000000.0).ToString('0.###', [Globalization.CultureInfo]::InvariantCulture)
    $html.AppendLine('<div><p class="priority-label">&#26368;&#20540;&#24471;&#20808;&#30475;&#30340;&#20301;&#32622;</p>') | Out-Null
    $html.AppendLine(("<div class='priority-time'>{0} &mdash; {1}</div><div class='priority-meta'>{2} ms</div>" -f
        (HtmlEncode (Format-ShortTime ([int64]$primaryEpisode.start_timestamp_ns))), (HtmlEncode (Format-ShortTime ([int64]$primaryEpisode.end_timestamp_ns))), $durationMs)) | Out-Null
    $html.AppendLine(("<div class='action'>&#24314;&#35696;&#22238; LeCroy GUI &#26597;&#30475; FAIL trace &#30340; <strong>{0} &mdash; {1}</strong>&#12290;</div>" -f (HtmlEncode (Format-ShortTime ([int64]$primaryEpisode.start_timestamp_ns))), (HtmlEncode (Format-ShortTime ([int64]$primaryEpisode.end_timestamp_ns))))) | Out-Null
    $primaryRatioText = Format-Percent ([double]$primaryEpisode.lfps_ratio)
    $html.AppendLine(("<div class='observation-summary'><strong>&#35264;&#23519;&#25688;&#35201;</strong><p>&#36889;&#19968;&#27573;&#21644;&#27491;&#24120;&#32000;&#37636;&#30340;&#34892;&#28858;&#24046;&#30064;&#24456;&#22823;&#12290;{0} ms &#20839;&#24190;&#20046;&#37117;&#26159; LFPS &#35338;&#34399;&#65292;&#36899;&#32218;&#29376;&#24907;&#35722;&#21270;&#20102; {1} &#27425;&#65292;&#32780;&#19988;&#27794;&#26377;&#30475;&#21040; LINK_CMD&#12290;</p></div>" -f $durationMs, (Format-Count ([int64]$primaryEpisode.ltssm_state_count)))) | Out-Null
    $html.AppendLine(("<div class='observe'><strong>&#20027;&#35201;&#35264;&#23519;</strong><ul><li>&#36899;&#32218;&#35338;&#34399;&#27604;&#20363;&#65288;LFPS&#65289;&#65306;{0}</li><li>&#36899;&#32218;&#29376;&#24907;&#35722;&#21270;&#65288;LTSSM&#65289;&#65306;{1} &#27425;</li><li>LINK_CMD &#21629;&#20196;&#65306;0 &#27425;</li></ul></div>" -f (HtmlEncode $primaryRatioText), (Format-Count ([int64]$primaryEpisode.ltssm_state_count)))) | Out-Null
}
else {
    $html.AppendLine('<p>&#27794;&#26377;&#29986;&#29983;&#20505;&#36984;&#21312;&#27573;&#12290;</p>') | Out-Null
}
$html.AppendLine('</section>') | Out-Null

if ($null -ne $primaryEpisode) {
    $baseLfpsRatio = Get-BaselineValue $baselineStats 'lfps_ratio'
    $baseLfps = Get-BaselineValue $baselineStats 'lfps_count'
    $baseLtssm = Get-BaselineValue $baselineStats 'ltssm_state_count'
    $baseLink = Get-BaselineValue $baselineStats 'link_cmd_count'
    $baseWindowMs = ([double]$data.windowing.window_ns / 1000000.0).ToString('0.###', [Globalization.CultureInfo]::InvariantCulture)
    $html.AppendLine(("<section class='section panel comparison' aria-labelledby='why-title'><h2 id='why-title'>&#21644;&#27491;&#24120;&#32000;&#37636;&#30456;&#27604;</h2><p class='small'>&#20197;&#19979;&#27604;&#36611;&#21839;&#38988;&#21312;&#27573;&#21644;&#27491;&#24120; PASS &#32000;&#37636;&#65292;&#24171;&#21161;&#20320;&#27770;&#23450;&#26159;&#21542;&#22238; GUI &#26597;&#30475;&#12290;</p><table><thead><tr><th>&#35264;&#23519;&#38917;&#30446;</th><th>&#21839;&#38988;&#21312;&#27573; {0} ms</th><th>&#27491;&#24120;&#32000;&#37636;&#21443;&#32771;&#20540;</th><th>&#21028;&#26039;</th></tr></thead><tbody>" -f $durationMs)) | Out-Null
    $comparisonRows = @(
        [pscustomobject]@{ label = '&#36899;&#32218;&#35338;&#34399;&#27604;&#20363;&#65288;LFPS&#65289;'; metric = 'lfps_ratio'; value = (Format-Percent ([double]$primaryEpisode.lfps_ratio)); baseline = (Format-Percent $baseLfpsRatio); rawValue = [double]$primaryEpisode.lfps_ratio; rawBaseline = $baseLfpsRatio },
        [pscustomobject]@{ label = '&#36899;&#32218;&#35338;&#34399;&#25976;&#37327;&#65288;LFPS&#65289;'; metric = 'LFPS'; value = (Format-Count ([int64]$primaryEpisode.lfps_count)); baseline = (Format-Count ([int64]$baseLfps)); rawValue = [double]$primaryEpisode.lfps_count; rawBaseline = $baseLfps },
        [pscustomobject]@{ label = '&#36899;&#32218;&#29376;&#24907;&#35722;&#21270;&#65288;LTSSM&#65289;'; metric = 'LTSSM'; value = (Format-Count ([int64]$primaryEpisode.ltssm_state_count)); baseline = (Format-Count ([int64]$baseLtssm)); rawValue = [double]$primaryEpisode.ltssm_state_count; rawBaseline = $baseLtssm },
        [pscustomobject]@{ label = 'LINK_CMD &#21629;&#20196;'; metric = 'LINK_CMD'; value = (Format-Count ([int64]$primaryEpisode.link_cmd_count)); baseline = (Format-Count ([int64]$baseLink)); rawValue = [double]$primaryEpisode.link_cmd_count; rawBaseline = $baseLink }
    )
    foreach ($row in $comparisonRows) {
        $delta = Get-DeltaText -Metric $row.metric -Value $row.rawValue -Baseline $row.rawBaseline
        $label = if ($row.label -match '&#') { $row.label } else { HtmlEncode $row.label }
        $html.AppendLine(("<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>" -f $label, (HtmlEncode $row.value), (HtmlEncode $row.baseline), $delta)) | Out-Null
    }
    $html.AppendLine("</tbody></table><p class='small'>&#27491;&#24120;&#32000;&#37636;&#21443;&#32771;&#20540;&#65306;&#25226;&#27491;&#24120; PASS trace &#20999;&#25104;&#24456;&#22810;&#20491; 10 ms &#23567;&#27573;&#65292;&#30475;&#30475;&#19968;&#33324;&#27491;&#24120;&#24773;&#27841;&#19979;&#36889;&#20123;&#25976;&#20540;&#22823;&#32004;&#26371;&#26159;&#22810;&#23569;&#12290;&#35443;&#32048;&#27604;&#36611;&#26041;&#24335;&#35531;&#30475;&#20998;&#26512;&#32048;&#31680;&#12290;</p></section>") | Out-Null

    $html.AppendLine('<section class="section panel" aria-labelledby="timeline-title"><h2 id="timeline-title">&#36889;&#27573;&#26178;&#38291;&#30332;&#29983;&#20102;&#20160;&#40636;</h2>') | Out-Null
    if ($null -ne $timelineSvg) {
        $html.AppendLine($timelineSvg) | Out-Null
        $html.AppendLine(("<p class='small'>&#22294;&#20363;&#65306;&#34253;&#33394;&#36234;&#23494;&#65292;&#34920;&#31034;&#35442;&#26178;&#38291;&#40670;&#20986;&#29694;&#36234;&#22810;&#36899;&#32218;&#35338;&#34399;&#65288;LFPS&#65289;&#65307;&#27224;&#33394;&#22291;&#40670;&#20195;&#34920;&#36899;&#32218;&#29376;&#24907;&#65288;LTSSM&#65289;&#30332;&#29983;&#35722;&#21270;&#12290;&#36889;&#24373;&#22294;&#20351;&#29992; FAIL trace &#20013;&#30340; {0} &#31558;&#23526;&#38555;&#35352;&#37636;&#65292;&#23565;&#25033;&#21040;&#19978;&#26041;&#30340;&#21839;&#38988;&#21312;&#27573;&#12290;</p>" -f (Format-Count ([int64]$localEvents.Count)))) | Out-Null
    }
    else {
        $html.AppendLine('<p class="warning">&#25214;&#19981;&#21040;&#21487;&#29992;&#30340; FAIL timeline &#20107;&#20214;&#36039;&#26009;&#65292;&#21482;&#33021;&#39023;&#31034;&#21312;&#27573;&#32113;&#35336;&#12290;&#35531;&#22238; LeCroy GUI &#30906;&#35469;&#36852;&#19968;&#31558; event &#20301;&#32622;&#12290;</p>') | Out-Null
    }
    $html.AppendLine('</section>') | Out-Null
}

$otherEpisodes = @($episodes | Select-Object -Skip 1)
if ($otherEpisodes.Count -gt 0) {
    $html.AppendLine('<section class="section" aria-labelledby="other-title"><h2 id="other-title">&#21478;&#19968;&#20491;&#20540;&#24471;&#27298;&#26597;&#30340;&#21312;&#27573;</h2><div class="other-list">') | Out-Null
    $candidateLetterCode = [int][char]'B'
    foreach ($episode in $otherEpisodes) {
        $otherStart = Format-Ns ([int64]$episode.start_timestamp_ns)
        $otherEnd = Format-Ns ([int64]$episode.end_timestamp_ns)
        $otherScore = ('{0:N3}' -f [double]$episode.score)
        $otherRanks = (@($episode.windows | ForEach-Object { '#' + $_.rank }) -join ', ')
        $candidateLetter = [char]$candidateLetterCode
        $html.AppendLine(("<article class='other-episode'><div class='other-head'><h3>&#21478;&#19968;&#20491;&#21312;&#27573;</h3></div><div class='other-time'>{1} &mdash; {2}</div><details><summary>&#26597;&#30475;&#36889;&#20491;&#21312;&#27573;</summary><p class='small'>&#36889;&#20491;&#21312;&#27573;&#21644;&#27491;&#24120; PASS &#32000;&#37636;&#30456;&#27604;&#65306;</p><ul class='reasons'>" -f
            $candidateLetter, (HtmlEncode $otherStart), (HtmlEncode $otherEnd), (HtmlEncode $otherRanks), (HtmlEncode $otherScore))) | Out-Null
        foreach ($reason in @($episode.reasons)) {
            $html.AppendLine(("<li>{0}</li>" -f (Get-LocalizedReason ([string]$reason)))) | Out-Null
        }
        $candidateLetterCode++
        $html.AppendLine(("</ul><details class='technical-detail'><summary>&#35443;&#32048;&#36039;&#26009;</summary><p class='small'>&#25490;&#24207;&#20998;&#25976;&#65306;{0}&#65288;&#21482;&#29992;&#20358;&#25490;&#21015;&#38918;&#24207;&#65292;&#19981;&#20195;&#34920;&#24037;&#20855;&#26377;&#22810;&#30906;&#23450;&#65289;&#12290;<br>C5 &#26178;&#38291;&#21312;&#27573;&#32232;&#34399;&#65306;{1}</p></details></details></article>" -f (HtmlEncode $otherScore), (HtmlEncode $otherRanks))) | Out-Null
    }
    $html.AppendLine('</div></section>') | Out-Null
}

$html.AppendLine('<section class="section details-grid">') | Out-Null
$html.AppendLine('<details><summary>&#20998;&#26512;&#32048;&#31680;</summary>') | Out-Null
if ($null -ne $primaryEpisode) {
    $detailRanks = (@($primaryEpisode.windows | ForEach-Object { '#' + $_.rank }) -join ', ')
    $detailScores = (@($primaryEpisode.windows | ForEach-Object { ('#{0} = {1:N3}' -f $_.rank, [double]$_.score) }) -join ', ')
    $html.AppendLine(("<p class='small'>&#20027;&#35201;&#21312;&#27573;&#65306;<code>{0} &mdash; {1}</code><br>&#31934;&#30906;&#26178;&#38291;&#65288;ns&#65289;&#65306;<code>{2} &mdash; {3}</code><br>C5 &#26178;&#38291;&#21312;&#27573;&#32232;&#34399;&#65306;<code>{4}</code><br>&#25490;&#24207;&#20998;&#25976;&#65288;&#21482;&#20379;&#25490;&#24207;&#65289;&#65306;<code>{5}</code><br>&#21312;&#27573;&#20839;&#23526;&#38555;&#35352;&#37636;&#25976;&#65306;<code>{6}</code><br>&#27604;&#36611;&#26041;&#24335;&#65306;PASS trace &#20998;&#25104;&#22810;&#20491; 10 ms &#21312;&#27573;&#65292;&#20351;&#29992;&#27491;&#24120;&#21312;&#27573;&#30340;&#32113;&#35336;&#20998;&#24067;&#20316;&#28858;&#21443;&#32771;&#65307;&#34920;&#26684;&#25505;&#29992; p95&#12290;</p>" -f
        (HtmlEncode (Format-ShortTime ([int64]$primaryEpisode.start_timestamp_ns))),
        (HtmlEncode (Format-ShortTime ([int64]$primaryEpisode.end_timestamp_ns))),
        (HtmlEncode $primaryEpisode.start_timestamp_ns),
        (HtmlEncode $primaryEpisode.end_timestamp_ns),
        (HtmlEncode $detailRanks),
        (HtmlEncode $detailScores),
        (Format-Count ([int64]$localEvents.Count)))) | Out-Null
}
$html.AppendLine(("<p class='small'>FAIL trace&#65306;<code>{0}</code><br>&#27491;&#24120; PASS trace&#65306;<code>{1}</code><br>&#20998;&#26512;&#29986;&#29289;&#65306;<code>{2}</code></p>" -f
    (HtmlEncode $failTraceName), (HtmlEncode $passTraceName), (HtmlEncode (Split-Path -Leaf $InputPath)))) | Out-Null
$html.AppendLine('</details>') | Out-Null

$html.AppendLine('<details><summary>&#25972;&#20221; PASS / FAIL &#35352;&#37636;&#32317;&#25976;</summary><p class="small">&#21482;&#29992;&#20358;&#35264;&#23519;&#25976;&#37327;&#24046;&#30064;&#65292;&#19981;&#20195;&#34920;&#25925;&#38556;&#21407;&#22240;&#12290;</p><table><thead><tr><th>&#35352;&#37636;&#39006;&#22411;</th><th>PASS</th><th>FAIL</th></tr></thead><tbody>') | Out-Null
foreach ($row in @(@('LINK_CMD','link_cmd'), @('LTSSM_STATE','ltssm_state'), @('LFPS','lfps'), @('&#20107;&#20214;&#32317;&#25976;','total_events'))) {
    $rowLabel = if ($row[0] -match '&#') { $row[0] } else { HtmlEncode $row[0] }
    $html.AppendLine(("<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>" -f $rowLabel, (Format-Count (Get-OverviewValue $data.pass_overview $row[1])), (Format-Count (Get-OverviewValue $data.fail_overview $row[1])))) | Out-Null
}
$html.AppendLine('</tbody></table></details>') | Out-Null

$rawDurationHint = $null
if ($null -ne $primaryEpisode) {
    $rawDurationHint = @($primaryEpisode.raw_signatures | ForEach-Object { [int64]$_.duration_ns } | Sort-Object -Descending | Select-Object -First 1)
}
$rawSummary = if ($rawDurationHint.Count -gt 0) { "&#21407;&#22987;&#36899;&#32218;&#35338;&#34399;&#29305;&#24501;&#65288;LFPS&#65292;&#21253;&#21547; $rawDurationHint ns&#65289;" } else { '&#21407;&#22987;&#36899;&#32218;&#35338;&#34399;&#29305;&#24501;&#65288;LFPS&#65289;' }
$html.AppendLine(("<details><summary>{0}</summary><div class='raw-table'><table><thead><tr><th>&#39006;&#22411;</th><th>&#27169;&#24335;</th><th>&#25345;&#32396;&#26178;&#38291;&#65288;ns&#65289;</th><th>&#26159;&#21542;&#28858;&#38283;&#22987;&#27169;&#24335;</th><th>&#25976;&#37327;</th></tr></thead><tbody>" -f $rawSummary)) | Out-Null
if ($null -ne $primaryEpisode) {
    foreach ($raw in @($primaryEpisode.raw_signatures)) {
        $html.AppendLine(("<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td></tr>" -f
            (HtmlEncode $raw.lfps_type), (HtmlEncode $raw.pattern_type), (HtmlEncode $raw.duration_ns), (HtmlEncode $raw.starts_pattern), (HtmlEncode (Format-Count ([int64]$raw.count))))) | Out-Null
    }
}
$html.AppendLine('</tbody></table></div></details>') | Out-Null

$integrityClass = if ($data.trace_integrity_qualified) { 'status' } else { 'warning' }
$integrityText = if ($data.trace_integrity_qualified) { 'PASS - &#21407;&#22987; trace &#30340;&#20358;&#28304;&#35657;&#25818;&#27794;&#26377;&#25913;&#35722;&#12290;' } else { 'NOT QUALIFIED - &#20351;&#29992;&#21069;&#35531;&#20808;&#27298;&#26597; JSON &#35657;&#25818;&#12290;' }
$html.AppendLine(("<details><summary>&#20358;&#28304;&#27284;&#26696;&#26159;&#21542;&#20445;&#25345;&#19981;&#35722;</summary><p class='{0}'>{1}</p><p class='small'>&#20358;&#28304;&#35657;&#25818;&#30001;&#19978;&#28216;&#30340;&#21807;&#35712; sandbox &#20445;&#35703;&#12290;</p>" -f $integrityClass, $integrityText)) | Out-Null
$html.AppendLine(("<p class='small'>PASS timeline&#65306;<code>{0}</code><br>FAIL timeline&#65306;<code>{1}</code><br>&#35222;&#31383;&#65306; {2} ms&#65307;&#27493;&#38263;&#65306; {3} ms&#65307;&#30456;&#23565; trace &#x5C0D;&#x9F4A;&#65306; {4}</p>" -f
    (HtmlEncode $passName), (HtmlEncode $failName), ([double]$data.windowing.window_ns / 1000000.0), ([double]$data.windowing.stride_ns / 1000000.0), ([bool]$data.absolute_cross_trace_alignment_used))) | Out-Null
$html.AppendLine('</details>') | Out-Null

$html.AppendLine('<details><summary>&#30446;&#21069;&#24037;&#20855;&#21487;&#20197;&#20570;&#20160;&#40636;</summary><p class="small">&#30446;&#21069;&#24037;&#20855;&#21487;&#20197;&#20570;&#20160;&#40636;&#65306;</p><ul class="reasons"><li>&#33258;&#21205;&#25214;&#20986;&#21644;&#27491;&#24120;&#32000;&#37636;&#24046;&#30064;&#36611;&#22823;&#30340;&#26178;&#38291;&#21312;&#27573;&#12290;</li><li>&#21578;&#35380;&#24037;&#31243;&#24107;&#25033;&#35442;&#20808;&#22238; LeCroy GUI &#26597;&#30475;&#21738;&#35041;&#12290;</li><li>&#19981;&#38656;&#35201;&#20107;&#20808;&#25552;&#20379;&#24050;&#30693;&#25925;&#38556;&#26178;&#38291;&#12290;</li></ul><p class="small">&#20998;&#26512;&#26041;&#24335;&#65306;</p><ul class="reasons"><li>PASS trace &#29992;&#20358;&#24314;&#31435;&#27491;&#24120;&#32000;&#37636;&#21443;&#32771;&#20540;&#12290;</li><li>PASS / FAIL &#21508;&#33258;&#20197;&#26178;&#38291;&#21312;&#27573;&#27604;&#36611;&#65292;&#19981;&#24375;&#34892;&#23565;&#40778;&#20841;&#20221; trace &#30340;&#26178;&#38291;&#12290;</li><li>LFPS &#21407;&#22987;&#20540;&#20445;&#30041;&#25976;&#23383;&#65292;&#19981;&#33258;&#34892;&#29468;&#28204; enum &#21517;&#31281;&#12290;</li><li>&#24037;&#31243;&#24107;&#27161;&#35352;&#30340;&#21312;&#22495;&#21482;&#29992;&#26044;&#20107;&#24460;&#39511;&#35657;&#65292;&#19981;&#26159;&#20998;&#26512;&#36664;&#20837;&#12290;</li></ul><p class="small">&#30446;&#21069;&#36996;&#19981;&#33021;&#20570;&#20160;&#40636;&#65306;</p><ul class="reasons"><li>&#21028;&#23450;&#30495;&#27491;&#25925;&#38556;&#21407;&#22240;&#12290;</li><li>&#21028;&#26039;&#25925;&#38556;&#22196;&#37325;&#31243;&#24230;&#12290;</li><li>&#33258;&#21205;&#21028;&#23450;&#29986;&#21697; PASS / FAIL&#12290;</li></ul>') | Out-Null
$html.AppendLine('</details></section>') | Out-Null

$html.AppendLine(("<footer>&#38626;&#32218;&#22577;&#21578;&#65307;&#20358;&#33258; <code>{0}</code>&#12290;JSON &#26159;&#27491;&#24335;&#20998;&#26512;&#36039;&#26009;&#12290;</footer>" -f (HtmlEncode (Split-Path -Leaf $InputPath)))) | Out-Null
$html.AppendLine('</main></body></html>') | Out-Null

[System.IO.File]::WriteAllText(
    $OutputPath,
    $html.ToString(),
    [System.Text.UTF8Encoding]::new($false))

$readBack = Get-Content -LiteralPath $OutputPath -Raw
if ($readBack -notmatch '<!doctype html>' -or
    $readBack -notmatch 'LeCroy Trace' -or
    $readBack -notmatch '&#26368;&#20540;&#24471;&#20808;&#30475;' -or
    $readBack -match '\?\?' -or
    $readBack -match '<script') {
    throw 'HTML report read-back verification failed.'
}
if ($null -ne $primaryEpisode -and $null -ne $failTimeline -and $readBack -notmatch '<svg') {
    throw 'Evidence timeline read-back verification failed.'
}

[pscustomobject]@{
    status = 'PASS'
    input = $InputPath
    output = $OutputPath
    candidate_count = $candidateList.Count
    episode_count = $episodes.Count
    primary_episode_windows = if ($null -ne $primaryEpisode) { $primaryEpisode.windows.Count } else { 0 }
    timeline_event_count = $localEvents.Count
    trace_names_loaded = ($null -ne $failTimeline -and $null -ne $passTimeline)
    bytes = (Get-Item -LiteralPath $OutputPath).Length
} | ConvertTo-Json -Compress
