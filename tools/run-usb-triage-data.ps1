<# Acquire additional protocol data from a controller-owned read-only copy. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$TracePath,
      [Parameter(Mandatory=$true)][string]$Output,
      [string]$ScriptPath)
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME 'Modules'
function Snapshot([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant();size=$i.Length;mtime=$i.LastWriteTimeUtc.ToString('o');readonly=[bool]$i.IsReadOnly}}
function Save([string]$p,$v){[IO.File]::WriteAllText($p,(ConvertTo-Json -InputObject $v -Depth 20),[Text.UTF8Encoding]::new($false))}
$work=(Resolve-Path -LiteralPath $TracePath).Path
$before=Snapshot $work
if(-not $before.readonly -or [IO.Path]::GetExtension($work) -ne '.usb'){throw 'Expected a controller-owned read-only .usb copy'}
if(Get-Process UsbSuite -ErrorAction SilentlyContinue){throw 'Existing LeCroy session; refusing acquisition'}
$out=[IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $out){throw 'Use a new output directory'}
[IO.Directory]::CreateDirectory($out) | Out-Null
# Resolve after creation: out-of-process COM cannot see a virtual MSIX path.
$out=(Resolve-Path -LiteralPath $out).Path
if(-not $ScriptPath){$ScriptPath=Join-Path $PSScriptRoot '../scripts/usb3-triage-data.vse'}
$script=(Resolve-Path -LiteralPath $ScriptPath).Path
$scriptBefore=Snapshot $script
$run=$null;$errorText='';$watch=[Diagnostics.Stopwatch]::StartNew()
try{
 Add-Type -Path (Join-Path $PSScriptRoot 'u01-selection-host.cs')
 $run=[U01Host]::Run($work,$script,(Join-Path $out 'lifecycle.log'))
 if($run.Error){$errorText=$run.Error}
}catch{$errorText=$_.Exception.GetBaseException().Message}
finally{[GC]::Collect();[GC]::WaitForPendingFinalizers();[GC]::Collect()}
$deadline=[DateTime]::UtcNow.AddSeconds(15)
while((Get-Process UsbSuite -ErrorAction SilentlyContinue) -and [DateTime]::UtcNow -lt $deadline){Start-Sleep -Milliseconds 250}
$after=Snapshot $work
$scriptAfter=Snapshot $script
$same=($before.sha256 -eq $after.sha256 -and $before.size -eq $after.size -and $before.mtime -eq $after.mtime -and $before.readonly -eq $after.readonly)
$nativeExited=-not [bool](Get-Process UsbSuite -ErrorAction SilentlyContinue)
$exe=$env:LECROY_USB_SUITE_EXE
if(-not $exe){$exe='C:\Program Files\LeCroy\USB Protocol Suite\UsbSuite.exe'}
$raw=[ordered]@{format='usb-protocol-data/v1';trace_sha256=$before.sha256;working_path=$work;before=$before;after=$after;
 script_sha256=$scriptBefore.sha256;script_unchanged=($scriptBefore.sha256 -eq $scriptAfter.sha256);
 run_result=if($run){$run.RunResult}else{-1};finished_result=if($run){$run.Sink.FinishedResult}else{-1};
 finished_count=if($run){$run.Sink.FinishedCount}else{0};reports=if($run){@($run.Sink.Reports.ToArray())}else{@()};
 error=$errorText;integrity_unchanged=$same;native_exited=$nativeExited;elapsed_ms=$watch.ElapsedMilliseconds;
 software_version=(Get-Item -LiteralPath $exe).VersionInfo.FileVersion}
Save (Join-Path $out 'raw-result.json') $raw
if(-not $same -or -not $nativeExited -or -not $raw.script_unchanged -or $errorText -or $raw.run_result -ne 2 -or $raw.finished_result -ne 2 -or $raw.finished_count -ne 1){throw 'Protocol acquisition incomplete; see raw-result.json'}
