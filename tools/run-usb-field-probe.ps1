[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$TracePath,
      [Parameter(Mandatory=$true)][string]$PlanDirectory,
      [Parameter(Mandatory=$true)][string]$Output,
      [Parameter(Mandatory=$true)][string]$Python)
$ErrorActionPreference='Stop'
function Snapshot([string]$p) {
    $i=Get-Item -LiteralPath $p
    return [ordered]@{sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant();size=$i.Length;mtime=$i.LastWriteTimeUtc.ToString('o');readonly=[bool]$i.IsReadOnly}
}
function Same($a,$b) {return ($a.sha256 -eq $b.sha256 -and $a.size -eq $b.size -and $a.mtime -eq $b.mtime -and $a.readonly -eq $b.readonly)}
function Save([string]$p,$v) {if(Test-Path -LiteralPath $p){throw 'Refuse overwrite'}; [IO.File]::WriteAllText($p,(ConvertTo-Json -InputObject $v -Depth 24),[Text.UTF8Encoding]::new($false))}
$source=(Resolve-Path -LiteralPath $TracePath).Path
$planRoot=(Resolve-Path -LiteralPath $PlanDirectory).Path
$planFile=Join-Path $planRoot 'plan.json'
$validator=Join-Path $PSScriptRoot 'usb_field_probe.py'
& $Python -X utf8 -B $validator check-plan --plan $planFile
if($LASTEXITCODE -ne 0){throw 'Field plan failed'}
$plan=Get-Content -LiteralPath $planFile -Raw | ConvertFrom-Json
$sourceBefore=Snapshot $source
if($sourceBefore.sha256 -ne $plan.trace_sha256 -or [IO.Path]::GetExtension($source) -ne '.usb'){throw 'Explicit USB source binding failed'}
$script=Join-Path $planRoot $plan.script
$scriptBefore=Snapshot $script
if($scriptBefore.sha256 -ne $plan.script_sha256){throw 'Script binding failed'}
$outPath=[IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $outPath){throw 'Refuse existing output'}
New-Item -ItemType Directory -Path $outPath | Out-Null
$work=Join-Path $outPath 'working.usb'
Copy-Item -LiteralPath $source -Destination $work
Set-ItemProperty -LiteralPath $work -Name IsReadOnly -Value $true
$before=Snapshot $work
if(-not $before.readonly -or $before.sha256 -ne $sourceBefore.sha256){throw 'Copy binding failed'}
$exe='C:\Program Files\LeCroy\USB Protocol Suite\UsbSuite.exe'
$constants='C:\Users\Public\Documents\LeCroy\USB Protocol Suite\Scripts\VFScripts\VS_constants.inc'
$vsTools='C:\Users\Public\Documents\LeCroy\USB Protocol Suite\Scripts\VFScripts\VSTools.inc'
$identities=[ordered]@{software_version=(Get-Item -LiteralPath $exe).VersionInfo.FileVersion;exe=Snapshot $exe;constants=Snapshot $constants;vstools=Snapshot $vsTools;host=Snapshot (Join-Path $PSScriptRoot 'u01-selection-host.cs');plan_sha256=(Snapshot $planFile).sha256}
Save (Join-Path $outPath 'before.json') ([ordered]@{source=$sourceBefore;working=$before;script=$scriptBefore;toolchain=$identities})
Add-Type -Path (Join-Path $PSScriptRoot 'u01-selection-host.cs')
$run=[U01Host]::Run($work,$script,(Join-Path $outPath 'lifecycle.log'))
[GC]::Collect(); [GC]::WaitForPendingFinalizers(); [GC]::Collect()
$after=Snapshot $work
$sourceAfter=Snapshot $source
$integrity=[ordered]@{source_unchanged=(Same $sourceBefore $sourceAfter);working_copy_unchanged=(Same $before $after);working_copy_readonly=($before.readonly -and $after.readonly)}
Save (Join-Path $outPath 'integrity.json') ([ordered]@{source_before=$sourceBefore;source_after=$sourceAfter;working_before=$before;working_after=$after})
$raw=[ordered]@{slice=$plan.slice;trace_sha256=$plan.trace_sha256;script_sha256=$plan.script_sha256;integrity=$integrity;run_result=$run.RunResult;finished_result=$run.Sink.FinishedResult;error=$run.Error;summary=$run.Sink.Summary;reports=@($run.Sink.Reports.ToArray())}
$resultFile=Join-Path $outPath 'result.json'
Save $resultFile $raw
if(-not $integrity.source_unchanged -or -not $integrity.working_copy_unchanged -or -not $integrity.working_copy_readonly){throw 'Integrity changed; stop'}
if(-not(Same $scriptBefore (Snapshot $script)) -or -not(Same $identities.constants (Snapshot $constants)) -or -not(Same $identities.vstools (Snapshot $vsTools))){throw 'Execution source changed'}
$text=& $Python -X utf8 -B $validator assess --plan $planFile --result $resultFile
if($LASTEXITCODE -ne 0){throw "Field reconciliation failed: $text"}
Save (Join-Path $outPath 'observations.json') ($text -join [Environment]::NewLine | ConvertFrom-Json)
$manifestText=& $Python -X utf8 -B $validator manifest --plan $planFile --result $resultFile --before (Join-Path $outPath 'before.json')
if($LASTEXITCODE -ne 0){throw "Field manifest failed: $manifestText"}
Save (Join-Path $outPath 'manifest.json') ($manifestText -join [Environment]::NewLine | ConvertFrom-Json)
Write-Output "$($plan.slice): native field sample reconciled; full qualification remains NOT_EVALUATED"
