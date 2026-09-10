param(
    [Parameter(Mandatory = $true)]
    [string] $PassTimelinePath,

    [Parameter(Mandatory = $true)]
    [string] $FailTimelinePath,

    [Parameter(Mandatory = $true)]
    [string] $OutputPath
)

$ErrorActionPreference = 'Stop'

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

function Get-EventSignature {
    param($Event)

    if ($Event.EventClass -eq 'LFPS') {
        return ('LFPS|{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}' -f
            $Event.Type,
            $Event.Raw.LfpsType,
            $Event.Raw.DurationNs,
            $Event.Raw.DurationSec,
            $Event.Raw.DurationRemainderNs,
            $Event.Raw.PatternType,
            $Event.Raw.StartsPattern,
            $Event.EventClass)
    }

    return ('{0}|{1}' -f $Event.EventClass, $Event.Type)
}

function Get-Signatures {
    param($Events)

    $list = [System.Collections.Generic.List[string]]::new()
    foreach ($event in @($Events)) {
        $list.Add((Get-EventSignature -Event $event))
    }
    return ,$list.ToArray()
}

function Get-WindowPositions {
    param(
        [string[]] $Signatures,
        [int] $Length
    )

    $positions = [System.Collections.Generic.Dictionary[string, System.Collections.Generic.List[int]]]::new()
    if ($Signatures.Length -lt $Length) {
        return $positions
    }

    for ($i = 0; $i -le $Signatures.Length - $Length; $i++) {
        $key = [string]::Join("`n", $Signatures[$i..($i + $Length - 1)])
        if (-not $positions.ContainsKey($key)) {
            $positions[$key] = [System.Collections.Generic.List[int]]::new()
        }
        $positions[$key].Add($i)
    }

    return $positions
}

function Get-Counts {
    param($Events)

    $counts = [ordered]@{
        LINK_CMD = 0
        LTSSM_STATE = 0
        LFPS = 0
    }

    foreach ($event in @($Events)) {
        if ($counts.Contains($event.EventClass)) {
            $counts[$event.EventClass]++
        }
    }

    return $counts
}

function Convert-TimeTextToSeconds {
    param([string] $Text)

    if ($Text -match '^\s*([0-9]+(?:\.[0-9]+)?)\s*(ns|us|ms|sec)\s*$') {
        $value = [double]$Matches[1]
        switch ($Matches[2]) {
            'ns' { return $value / 1000000000.0 }
            'us' { return $value / 1000000.0 }
            'ms' { return $value / 1000.0 }
            'sec' { return $value }
        }
    }

    return $null
}

$passEvents = @($pass.events)
$failEvents = @($fail.events)
$passSignatures = Get-Signatures -Events $passEvents
$failSignatures = Get-Signatures -Events $failEvents

$anchorLength = 5
$passWindows = Get-WindowPositions -Signatures $passSignatures -Length $anchorLength
$failWindows = Get-WindowPositions -Signatures $failSignatures -Length $anchorLength
$anchor = $null

foreach ($entry in $passWindows.GetEnumerator()) {
    if ($entry.Value.Count -eq 1 -and
        $failWindows.ContainsKey($entry.Key) -and
        $failWindows[$entry.Key].Count -eq 1) {
        $anchor = [pscustomobject]@{
            status = 'FOUND'
            length = $anchorLength
            pass_index = $entry.Value[0]
            fail_index = $failWindows[$entry.Key][0]
            signature = $entry.Key -replace "`n", ' > '
        }
        break
    }
}

$candidate = [ordered]@{
    status = 'NOT_EVALUATED'
    claim = 'candidate divergence'
    pass_index = $null
    fail_index = $null
    pass_timestamp = $null
    fail_timestamp = $null
    pass_suggested_window = $null
    fail_suggested_window = $null
    pass_window = @()
    fail_window = @()
}

if ($null -eq $anchor) {
    $candidate.status = 'NO_RELIABLE_COMMON_ANCHOR'
}
else {
    $candidate.status = 'EVALUATED_AFTER_ANCHOR'
    $maxCompare = [Math]::Min(
        1000,
        [Math]::Min(
            $passSignatures.Length - $anchor.pass_index,
            $failSignatures.Length - $anchor.fail_index))
    $mismatchOffset = $null

    for ($offset = $anchorLength; $offset -lt $maxCompare; $offset++) {
        if ($passSignatures[$anchor.pass_index + $offset] -ne
            $failSignatures[$anchor.fail_index + $offset]) {
            $mismatchOffset = $offset
            break
        }
    }

    if ($null -eq $mismatchOffset) {
        $candidate.status = 'NO_DIVERGENCE_WITHIN_COMPARE_WINDOW'
    }
    else {
        $passIndex = $anchor.pass_index + $mismatchOffset
        $failIndex = $anchor.fail_index + $mismatchOffset
        $candidate.pass_index = $passIndex
        $candidate.fail_index = $failIndex
        $candidate.pass_timestamp = $passEvents[$passIndex].Timestamp
        $candidate.fail_timestamp = $failEvents[$failIndex].Timestamp

        $passSeconds = Convert-TimeTextToSeconds -Text $candidate.pass_timestamp
        $failSeconds = Convert-TimeTextToSeconds -Text $candidate.fail_timestamp
        if ($null -ne $passSeconds) {
            $candidate.pass_suggested_window = [ordered]@{
                start_seconds = [Math]::Max(0, $passSeconds - 0.1)
                end_seconds = $passSeconds + 0.1
            }
        }
        if ($null -ne $failSeconds) {
            $candidate.fail_suggested_window = [ordered]@{
                start_seconds = [Math]::Max(0, $failSeconds - 0.1)
                end_seconds = $failSeconds + 0.1
            }
        }

        $passStart = [Math]::Max(0, $passIndex - 2)
        $passEnd = [Math]::Min($passEvents.Length - 1, $passIndex + 2)
        $failStart = [Math]::Max(0, $failIndex - 2)
        $failEnd = [Math]::Min($failEvents.Length - 1, $failIndex + 2)
        $candidate.pass_window = @($passEvents[$passStart..$passEnd])
        $candidate.fail_window = @($failEvents[$failStart..$failEnd])
    }
}

$artifact = [ordered]@{
    comparison = 'M2 / DEMO-1 PASS vs FAIL candidate comparison'
    pass_timeline = $PassTimelinePath
    fail_timeline = $FailTimelinePath
    pass_counts = Get-Counts -Events $passEvents
    fail_counts = Get-Counts -Events $failEvents
    pass_total = $passEvents.Length
    fail_total = $failEvents.Length
    anchor = $anchor
    candidate_divergence = $candidate
    claims = @(
        'This output identifies a candidate divergence after a common sequence anchor when one is found.',
        'It does not claim absolute first divergence, root cause, severity, or PASS/FAIL classification.',
        'Timestamp windows are trace-local and are not directly aligned across captures.'
    )
}

$json = $artifact | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText(
    $OutputPath,
    $json + [Environment]::NewLine,
    [System.Text.UTF8Encoding]::new($false)
)

$readBack = Get-Content -LiteralPath $OutputPath -Raw | ConvertFrom-Json
[pscustomobject]@{
    output_path = $OutputPath
    pass_total = $readBack.pass_total
    fail_total = $readBack.fail_total
    pass_counts = ($readBack.pass_counts | ConvertTo-Json -Compress)
    fail_counts = ($readBack.fail_counts | ConvertTo-Json -Compress)
    anchor_status = $readBack.anchor.status
    candidate_status = $readBack.candidate_divergence.status
    pass_timestamp = $readBack.candidate_divergence.pass_timestamp
    fail_timestamp = $readBack.candidate_divergence.fail_timestamp
    pass_suggested_window = ($readBack.candidate_divergence.pass_suggested_window | ConvertTo-Json -Compress)
    fail_suggested_window = ($readBack.candidate_divergence.fail_suggested_window | ConvertTo-Json -Compress)
} | ConvertTo-Json -Compress
