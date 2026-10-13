<# Independent U01 runner. Without -Execute it only checks saved plans and files.
   Each explicit execution uses a NEW read-only working copy. No saves, capture,
   hardware commands, historical-output writes or existing pipeline changes. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$TracePath,
    [Parameter(Mandatory=$true)][string]$PlanDirectory,
    [Parameter(Mandatory=$true)][string]$Output,
    [Parameter(Mandatory=$true)][string]$Python,
    [switch]$Execute
)
$ErrorActionPreference = 'Stop'
function Snapshot([string]$Path) {
    $item = Get-Item -LiteralPath $Path
    if ($item.PSIsContainer) { throw 'Expected a file' }
    return [ordered]@{ sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant();
        size=$item.Length; mtime=$item.LastWriteTimeUtc.ToString('o'); readonly=[bool]$item.IsReadOnly }
}
function Same($a,$b) { return ($a.sha256 -eq $b.sha256 -and $a.size -eq $b.size -and $a.mtime -eq $b.mtime -and $a.readonly -eq $b.readonly) }
function Save([string]$Path,$Value) {
    if (Test-Path -LiteralPath $Path) { throw "Refusing to overwrite $Path" }
    [IO.File]::WriteAllText($Path,(ConvertTo-Json -InputObject $Value -Depth 24),[Text.UTF8Encoding]::new($false))
}
$source = (Resolve-Path -LiteralPath $TracePath).Path
$planRoot = (Resolve-Path -LiteralPath $PlanDirectory).Path
$planFile = Join-Path $planRoot 'plan.json'
$plan = Get-Content -LiteralPath $planFile -Raw | ConvertFrom-Json
$assessor = Join-Path $PSScriptRoot 'u01_selection.py'
# The Python validator enforces all settings, filenames and template hashes.
& $Python -X utf8 -B $assessor check-plan --plan $planFile
if ($LASTEXITCODE -ne 0) { throw 'Plan validation failed' }
$sourceBefore = Snapshot $source
if ($sourceBefore.sha256 -ne $plan.trace_sha256) { throw 'Source does not match reviewed plan identity' }
if ([IO.Path]::GetExtension($source) -ne '.usb') { throw 'Expected an explicit USB trace input' }
foreach ($profile in $plan.profiles) {
    $script = Join-Path $planRoot $profile.script
    if ((Snapshot $script).sha256 -ne $profile.script_sha256) { throw 'Prepared script identity mismatch' }
}
$manualPath = 'C:\Program Files\LeCroy\USB Protocol Suite\Documents\USBProtocolSuiteVSEManual.pdf'
$constantsPath = 'C:\Users\Public\Documents\LeCroy\USB Protocol Suite\Scripts\VFScripts\VS_constants.inc'
$exePath = 'C:\Program Files\LeCroy\USB Protocol Suite\UsbSuite.exe'
$manualSha = (Snapshot $manualPath).sha256
$constantsSha = (Snapshot $constantsPath).sha256
$softwareVersion = (Get-Item -LiteralPath $exePath).VersionInfo.FileVersion
$outPath = [IO.Path]::GetFullPath($Output)
if (Test-Path -LiteralPath $outPath) { throw 'Refusing existing output directory' }
New-Item -ItemType Directory -Path $outPath | Out-Null
Save (Join-Path $outPath 'preflight.json') ([ordered]@{source=$source; source_before=$sourceBefore;
    plan_sha256=(Snapshot $planFile).sha256; software_version=$softwareVersion; executable_sha256=(Snapshot $exePath).sha256;
    manual_sha256=$manualSha; constants_sha256=$constantsSha; execute_requested=[bool]$Execute;
    raw_trace_opened=$false; qualification='NOT_EVALUATED'})
if (-not $Execute) { Write-Output 'Preflight complete; no COM activation. Use -Execute only under runtime authorization.'; return }
Add-Type -Path (Join-Path $PSScriptRoot 'u01-selection-host.cs')
foreach ($profile in $plan.profiles) {
    $runDir = Join-Path $outPath $profile.id
    New-Item -ItemType Directory -Path $runDir | Out-Null
    $work = Join-Path $runDir 'working.usb'
    Copy-Item -LiteralPath $source -Destination $work
    Set-ItemProperty -LiteralPath $work -Name IsReadOnly -Value $true
    $before = Snapshot $work
    if (-not $before.readonly -or $before.sha256 -ne $sourceBefore.sha256) { throw 'Copy identity or read-only gate failed' }
    $script = Join-Path $planRoot $profile.script
    if ((Snapshot $script).sha256 -ne $profile.script_sha256 -or -not (Same $sourceBefore (Snapshot $source)) -or
        (Snapshot $manualPath).sha256 -ne $manualSha -or (Snapshot $constantsPath).sha256 -ne $constantsSha) { throw 'Input changed before execution' }
    $run = [U01Host]::Run($work,$script,(Join-Path $runDir 'lifecycle.log'))
    [GC]::Collect(); [GC]::WaitForPendingFinalizers(); [GC]::Collect()
    $after = Snapshot $work
    $sourceAfter = Snapshot $source
    $integrity = [ordered]@{ source_unchanged=(Same $sourceBefore $sourceAfter);
        working_copy_unchanged=(Same $before $after); working_copy_readonly=($before.readonly -and $after.readonly) }
    Save (Join-Path $runDir 'integrity.json') ([ordered]@{source_before=$sourceBefore; source_after=$sourceAfter; working_before=$before; working_after=$after})
    $raw = [ordered]@{ selection=$profile.id; trace_sha256=$sourceBefore.sha256; script_sha256=$profile.script_sha256;
        integrity=$integrity; run_result=$run.RunResult; finished_result=$run.Sink.FinishedResult; error=$run.Error;
        rows=@($run.Sink.Rows.ToArray()); summary=$run.Sink.Summary;
        software_version=$softwareVersion; constants_sha256=$constantsSha; manual_sha256=$manualSha }
    $rawPath = Join-Path $runDir 'result.json'
    Save $rawPath $raw
    Save (Join-Path $runDir 'reports.json') @($run.Sink.Reports.ToArray())
    if (-not $integrity.source_unchanged -or -not $integrity.working_copy_unchanged -or -not $integrity.working_copy_readonly) { throw 'Integrity changed; stop all subsequent selections' }
    if ((Snapshot $script).sha256 -ne $profile.script_sha256 -or (Snapshot $manualPath).sha256 -ne $manualSha -or
        (Snapshot $constantsPath).sha256 -ne $constantsSha) { throw 'Script or installed source changed during execution' }
    $assessmentText = & $Python -X utf8 -B $assessor assess --plan $planFile --result $rawPath --selection $profile.id
    if ($LASTEXITCODE -ne 0) { throw "Result reconciliation failed for $($profile.id): $assessmentText" }
    Save (Join-Path $runDir 'assessment.json') ($assessmentText -join [Environment]::NewLine | ConvertFrom-Json)
    Write-Output "$($profile.id): transport checked; coverage qualification remains NOT_EVALUATED"
}
$comparisonText = & $Python -X utf8 -B $assessor compare --plan $planFile --results-directory $outPath
if ($LASTEXITCODE -ne 0) { throw "Selection comparison failed: $comparisonText" }
Save (Join-Path $outPath 'comparison.json') ($comparisonText -join [Environment]::NewLine | ConvertFrom-Json)
