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
$passEvents = @($pass.events)
$failEvents = @($fail.events)

# These are expert-labeled values from the known FAIL trace. They select a
# ground-truth region; they are not a decoder or an LFPS enum interpretation.
$groundTruthStartNs = [int64]21789454560
$groundTruthEndNs = [int64]21801473168
$seedLfpsType = [int64]74
$seedDurationNs = [int64]2200
$seedPatternType = [int64]4
$seedStartsPattern = [int64]1
$contextBefore = 12
$contextAfter = 12
$relativeGapQuantumNs = [int64]1000

function Test-HasTimestampFields {
    param($Event)

    return (
        $null -ne $Event.TimestampNs -and
        $null -ne $Event.TimestampSeconds -and
        $null -ne $Event.TimestampNanoseconds
    )
}

function Get-SemanticSignature {
    param($Event)

    if ($Event.EventClass -eq 'LFPS') {
        if ($null -eq $Event.Raw) {
            return $null
        }

        return ('LFPS|{0}|{1}|{2}|{3}|{4}|{5}' -f
            $Event.Type,
            [int64]$Event.Raw.LfpsType,
            [int64]$Event.Raw.PatternType,
            [int64]$Event.Raw.DurationNs,
            [int64]$Event.Raw.DurationRemainderNs,
            [int64]$Event.Raw.StartsPattern)
    }

    if ($Event.EventClass -eq 'LINK_CMD' -or
        $Event.EventClass -eq 'LTSSM_STATE') {
        return ('{0}|{1}' -f $Event.EventClass, $Event.Type)
    }

    return $null
}

function Get-RelativeGapBucket {
    param(
        [int64] $PreviousTimestampNs,
        [int64] $TimestampNs
    )

    $gap = $TimestampNs - $PreviousTimestampNs
    if ($gap -lt 0) {
        return 'INVALID'
    }

    return [string][int64](($gap + ($relativeGapQuantumNs / 2)) / $relativeGapQuantumNs)
}

function Get-FingerprintKey {
    param(
        [object[]] $Events,
        [int] $Start,
        [int] $Length
    )

    $parts = [System.Collections.Generic.List[string]]::new()
    $firstSignature = Get-SemanticSignature -Event $Events[$Start]
    if ($null -eq $firstSignature) {
        return $null
    }

    $parts.Add($firstSignature)
    for ($offset = 1; $offset -lt $Length; $offset++) {
        $previous = $Events[$Start + $offset - 1]
        $current = $Events[$Start + $offset]
        $signature = Get-SemanticSignature -Event $current
        if ($null -eq $signature) {
            return $null
        }

        $gapBucket = Get-RelativeGapBucket `
            -PreviousTimestampNs ([int64]$previous.TimestampNs) `
            -TimestampNs ([int64]$current.TimestampNs)
        if ($gapBucket -eq 'INVALID') {
            return $null
        }

        $parts.Add(('{0}|gap_us={1}' -f $signature, $gapBucket))
    }

    return [string]::Join("`n", $parts.ToArray())
}

function Get-EventWindow {
    param(
        [object[]] $Events,
        [int] $Start,
        [int] $Length
    )

    return @($Events[$Start..($Start + $Length - 1)])
}

function Get-WindowSummary {
    param(
        [object[]] $Events,
        [int] $Start,
        [int] $Length
    )

    $window = Get-EventWindow -Events $Events -Start $Start -Length $Length
    return [ordered]@{
        start_array_index = $Start
        end_array_index = $Start + $Length - 1
        start_event_index = [int64]$window[0].Index
        end_event_index = [int64]$window[$window.Count - 1].Index
        start_timestamp_ns = [int64]$window[0].TimestampNs
        end_timestamp_ns = [int64]$window[$window.Count - 1].TimestampNs
        event_count = $window.Count
    }
}

function Get-SeedPositions {
    param(
        [object[]] $Events,
        [bool] $RestrictToGroundTruth
    )

    $positions = [System.Collections.Generic.List[int]]::new()
    for ($i = 0; $i -lt $Events.Count; $i++) {
        $event = $Events[$i]
        if ($event.EventClass -ne 'LFPS' -or $null -eq $event.Raw) {
            continue
        }

        if ([int64]$event.Raw.LfpsType -ne $seedLfpsType -or
            [int64]$event.Raw.DurationNs -ne $seedDurationNs -or
            [int64]$event.Raw.PatternType -ne $seedPatternType -or
            [int64]$event.Raw.StartsPattern -ne $seedStartsPattern) {
            continue
        }

        if ($RestrictToGroundTruth -and
            ([int64]$event.TimestampNs -lt $groundTruthStartNs -or
             [int64]$event.TimestampNs -gt $groundTruthEndNs)) {
            continue
        }

        $positions.Add($i)
    }

    return $positions.ToArray()
}

$allEvents = @($passEvents) + @($failEvents)
$timestampFieldsPresent = $true
foreach ($event in $allEvents) {
    if (-not (Test-HasTimestampFields -Event $event)) {
        $timestampFieldsPresent = $false
        break
    }
}

$timelineIntegrityQualified = (
    $pass.trace_integrity_unchanged -eq $true -and
    $fail.trace_integrity_unchanged -eq $true
)

$fingerprintLength = 1 + $contextBefore + $contextAfter
$failTargetSeeds = @()
$failTargetFingerprint = $null
$failTargetStart = $null
$failTargetSeedIndex = $null
$failTargetSeedCount = 0
$passMatches = @()
$failFingerprintMatches = @()
$status = 'SEMANTIC_COVERAGE_INSUFFICIENT'
$reason = 'Unified timelines do not contain C3 timestamp components.'

if ($timestampFieldsPresent) {
    $failTargetSeeds = @(Get-SeedPositions -Events $failEvents -RestrictToGroundTruth $true)
    $failTargetSeedCount = $failTargetSeeds.Count

    if ($failTargetSeeds.Count -eq 0) {
        $reason = 'The expert-labeled FAIL region did not contain the verified raw LFPS seed.'
    }
    else {
        $failTargetSeedIndex = $failTargetSeeds[0]
        if ($failTargetSeedIndex -lt $contextBefore -or
            ($failTargetSeedIndex + $contextAfter) -ge $failEvents.Count) {
            $reason = 'The FAIL seed did not have the required semantic context.'
        }
        else {
            $failTargetStart = $failTargetSeedIndex - $contextBefore
            $failTargetFingerprint = Get-FingerprintKey `
                -Events $failEvents `
                -Start $failTargetStart `
                -Length $fingerprintLength

            if ($null -eq $failTargetFingerprint) {
                $reason = 'The FAIL semantic fingerprint could not be constructed.'
            }
            else {
                $failSeedPositions = @(Get-SeedPositions -Events $failEvents -RestrictToGroundTruth $false)
                foreach ($seedPosition in $failSeedPositions) {
                    if ($seedPosition -lt $contextBefore -or
                        ($seedPosition + $contextAfter) -ge $failEvents.Count) {
                        continue
                    }

                    $start = $seedPosition - $contextBefore
                    $key = Get-FingerprintKey -Events $failEvents -Start $start -Length $fingerprintLength
                    if ($key -eq $failTargetFingerprint) {
                        $failFingerprintMatches += $start
                    }
                }

                $passSeedPositions = @(Get-SeedPositions -Events $passEvents -RestrictToGroundTruth $false)
                foreach ($seedPosition in $passSeedPositions) {
                    if ($seedPosition -lt $contextBefore -or
                        ($seedPosition + $contextAfter) -ge $passEvents.Count) {
                        continue
                    }

                    $start = $seedPosition - $contextBefore
                    $key = Get-FingerprintKey -Events $passEvents -Start $start -Length $fingerprintLength
                    if ($key -eq $failTargetFingerprint) {
                        $passMatches += $start
                    }
                }

                if ($failFingerprintMatches.Count -ne 1) {
                    $status = 'MULTIPLE_SEMANTIC_MATCHES'
                    $reason = 'The FAIL semantic fingerprint was not unique within the extracted FAIL timeline.'
                }
                elseif ($passMatches.Count -eq 0) {
                    $status = 'NO_RELIABLE_SEMANTIC_MATCH'
                    $reason = 'No PASS timeline region matched the verified raw-field and relative-gap fingerprint.'
                }
                elseif ($passMatches.Count -gt 1) {
                    $status = 'MULTIPLE_SEMANTIC_MATCHES'
                    $reason = 'More than one PASS timeline region matched the verified semantic fingerprint.'
                }
                else {
                    $status = 'SEMANTIC_MATCH_FOUND'
                    $reason = 'Exactly one PASS and one FAIL region matched the verified semantic fingerprint.'
                }
            }
        }
    }
}

$failWindow = $null
$passWindow = $null
if ($null -ne $failTargetStart) {
    $failWindow = Get-WindowSummary -Events $failEvents -Start $failTargetStart -Length $fingerprintLength
}
if ($passMatches.Count -eq 1) {
    $passWindow = Get-WindowSummary -Events $passEvents -Start $passMatches[0] -Length $fingerprintLength
}

$guiHandoff = [ordered]@{
    emitted = ($status -eq 'SEMANTIC_MATCH_FOUND')
    pass = $null
    fail = $null
    claim = 'GUI handoff is emitted only for one reliable semantic match.'
}
if ($status -eq 'SEMANTIC_MATCH_FOUND') {
    $guiHandoff.pass = $passWindow
    $guiHandoff.fail = $failWindow
}

$artifact = [ordered]@{
    comparison = 'C4 semantic alignment using verified raw fields'
    pass_timeline = $PassTimelinePath
    fail_timeline = $FailTimelinePath
    status = $status
    reason = $reason
    qualification = 'PASS_FAIL_CLOSED'
    ground_truth_fail_region = [ordered]@{
        start_timestamp_ns = $groundTruthStartNs
        end_timestamp_ns = $groundTruthEndNs
        source = 'expert-labeled FAIL GUI observation'
    }
    seed = [ordered]@{
        event_class = 'LFPS'
        lfps_type = $seedLfpsType
        duration_ns = $seedDurationNs
        pattern_type = $seedPatternType
        starts_pattern = $seedStartsPattern
        interpretation = 'raw values only; no enum name inferred'
    }
    fingerprint = [ordered]@{
        context_before = $contextBefore
        context_after = $contextAfter
        length = $fingerprintLength
        relative_gap_quantum_ns = $relativeGapQuantumNs
        uses_absolute_cross_trace_timestamp = $false
        uses_verified_raw_fields = $true
    }
    timestamp_fields_present = $timestampFieldsPresent
    timeline_trace_integrity_qualified = $timelineIntegrityQualified
    fail_target_seed_count = $failTargetSeedCount
    fail_fingerprint_match_count = $failFingerprintMatches.Count
    pass_fingerprint_match_count = $passMatches.Count
    fail_target_window = $failWindow
    pass_match_window = $passWindow
    gui_handoff = $guiHandoff
    claims = @(
        'The comparison uses raw VSE-exposed fields and relative timing buckets; it does not infer LFPS enum names.',
        'Absolute trace timestamps are not used to align PASS and FAIL captures.',
        'No GUI handoff is emitted unless exactly one semantic fingerprint match exists on each side.',
        'This result does not claim root cause, severity, or automatic PASS/FAIL classification.'
    )
}

[System.IO.File]::WriteAllText(
    $OutputPath,
    (($artifact | ConvertTo-Json -Depth 20) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false))

$readBack = Get-Content -LiteralPath $OutputPath -Raw | ConvertFrom-Json
if ($readBack.status -ne $artifact.status -or
    $readBack.gui_handoff.emitted -ne $artifact.gui_handoff.emitted) {
    throw 'C4 semantic alignment JSON read-back verification failed.'
}

[pscustomobject]@{
    output_path = $OutputPath
    status = $readBack.status
    reason = $readBack.reason
    timestamp_fields_present = $readBack.timestamp_fields_present
    timeline_trace_integrity_qualified = $readBack.timeline_trace_integrity_qualified
    fail_target_seed_count = $readBack.fail_target_seed_count
    fail_fingerprint_match_count = $readBack.fail_fingerprint_match_count
    pass_fingerprint_match_count = $readBack.pass_fingerprint_match_count
    gui_handoff_emitted = $readBack.gui_handoff.emitted
} | ConvertTo-Json -Compress
