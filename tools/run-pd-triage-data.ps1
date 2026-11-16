<# Native grouping first, minimal VSE only for packet/header evidence. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$TracePath,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME 'Modules'
function Snapshot([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant();size=$i.Length;mtime=$i.LastWriteTimeUtc.ToString('o');readonly=[bool]$i.IsReadOnly}}
function Save([string]$p,$v){[IO.File]::WriteAllText($p,(ConvertTo-Json -InputObject $v -Depth 20),[Text.UTF8Encoding]::new($false))}
$work=(Resolve-Path -LiteralPath $TracePath).Path;$before=Snapshot $work
if(-not $before.readonly){throw 'PD acquisition requires owned read-only copy'}
$out=[IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $out){throw 'Use a new PD output directory'}
[IO.Directory]::CreateDirectory($out) | Out-Null;$out=(Resolve-Path -LiteralPath $out).Path
& (Join-Path $PSScriptRoot 'run-usb-triage-data.ps1') -TracePath $work -Output (Join-Path $out 'headers') -ScriptPath (Join-Path $PSScriptRoot '../scripts/pd-triage-headers.vse')
if(Get-Process UsbSuite -ErrorAction SilentlyContinue){throw 'Header worker not closed; refusing Automation activation'}
$app=$null;$trace=$null;$owned=$null;$caption=$null;$errorText='';$exports=@();$watch=[Diagnostics.Stopwatch]::StartNew()
try{
 $app=[U01Host]::Activate({New-Object -ComObject CATC.UsbTracer},$null)
 $all=@(Get-Process UsbSuite -ErrorAction SilentlyContinue)
 if($all.Count -ne 1){throw 'Cannot establish exclusive Automation process ownership'}
 $owned=$all[0];$start=$owned.StartTime.ToUniversalTime().Ticks
 $trace=$app.OpenFile($work);$owned.Refresh();$caption=$owned.MainWindowTitle
 if(-not $caption.Contains([IO.Path]::GetFileName($work))){throw 'Native caption does not identify bound copy'}
 foreach($pair in @(@(1,'transactions.csv'),@(3,'transfers.csv'))){
  $file=Join-Path $out $pair[1]
  try{
   $current=@(Get-Process UsbSuite -ErrorAction SilentlyContinue)
   if($current.Count -ne 1 -or $current[0].Id -ne $owned.Id -or $current[0].StartTime.ToUniversalTime().Ticks -ne $start -or $current[0].MainWindowTitle -ne $caption){throw 'Owned native session changed'}
   $trace.ExportToCsv($file,[int]$pair[0],-1,-1)
   $exports+=,[ordered]@{level=$pair[0];file=$pair[1];state=if(Test-Path -LiteralPath $file){'returned'}else{'no_output'};identity=if(Test-Path -LiteralPath $file){Snapshot $file}else{$null}}
  }catch{$exports+=,[ordered]@{level=$pair[0];file=$pair[1];state='error';error=$_.Exception.GetBaseException().Message;identity=$null}}
 }
}catch{$errorText=$_.Exception.GetBaseException().Message}
finally{
 if($trace){
  try{
   $current=@(Get-Process UsbSuite -ErrorAction SilentlyContinue)
   if($current.Count -eq 1 -and $current[0].Id -eq $owned.Id -and $current[0].StartTime.ToUniversalTime().Ticks -eq $start -and $current[0].MainWindowTitle -eq $caption){$trace.Close()}
   else{$errorText+=' Native ownership changed; Close refused.'}
  }catch{$errorText+=' Close: '+$_.Exception.GetBaseException().Message}
 }
 foreach($value in @($trace,$app)){if($value){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($value)}}
 [GC]::Collect();[GC]::WaitForPendingFinalizers();[GC]::Collect()
}
$deadline=[DateTime]::UtcNow.AddSeconds(15)
while((Get-Process UsbSuite -ErrorAction SilentlyContinue) -and [DateTime]::UtcNow -lt $deadline){Start-Sleep -Milliseconds 250}
$after=Snapshot $work;$same=($before.sha256 -eq $after.sha256 -and $before.size -eq $after.size -and $before.mtime -eq $after.mtime -and $before.readonly -eq $after.readonly)
$result=[ordered]@{format='pd-native-data/v1';trace_sha256=$before.sha256;before=$before;after=$after;integrity_unchanged=$same;native_exited=(-not [bool](Get-Process UsbSuite -ErrorAction SilentlyContinue));owned_pid=if($owned){$owned.Id}else{$null};owned_start_ticks=$start;bound_caption=$caption;error=$errorText;exports=$exports;elapsed_ms=$watch.ElapsedMilliseconds;header_raw_sha256=(Snapshot (Join-Path $out 'headers/raw-result.json')).sha256}
Save (Join-Path $out 'raw-result.json') $result
if(-not $same -or -not $result.native_exited -or $errorText){throw 'PD native acquisition incomplete; inspect raw-result.json'}
