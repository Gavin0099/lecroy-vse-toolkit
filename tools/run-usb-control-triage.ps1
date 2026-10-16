<# Single input, source-preserving USB2 control-transfer inspection report. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$TracePath,
    [Parameter(Mandatory=$true)][string]$Output,
    [string]$Python='python',
    [ValidateSet('Automation','Vse')][string]$Backend='Vse'
)
$ErrorActionPreference='Stop'
function Snapshot([string]$p) {
    $i=Get-Item -LiteralPath $p
    [ordered]@{sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant();
        size=$i.Length;mtime=$i.LastWriteTimeUtc.ToString('o');readonly=[bool]$i.IsReadOnly}
}
function Same($a,$b) { $a.sha256 -eq $b.sha256 -and $a.size -eq $b.size -and $a.mtime -eq $b.mtime -and $a.readonly -eq $b.readonly }
function Save([string]$p,$v) {
    if(Test-Path -LiteralPath $p){throw "Refusing overwrite: $p"}
    [IO.File]::WriteAllText($p,(ConvertTo-Json -InputObject $v -Depth 16),[Text.UTF8Encoding]::new($false))
}
$source=(Resolve-Path -LiteralPath $TracePath).Path
if([IO.Path]::GetExtension($source) -ne '.usb'){throw 'Expected one .usb trace'}
$out=[IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $out){throw 'Use a new output directory'}
if(Get-Process UsbSuite -ErrorAction SilentlyContinue){throw 'UsbSuite is already running; close it before an isolated run'}
$script=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../scripts/usb-control-transfers.vse')).Path
$hostFile=Join-Path $PSScriptRoot 'u01-selection-host.cs'
$analyzer=Join-Path $PSScriptRoot 'usb_control_triage.py'
if(-not(Test-Path -LiteralPath $analyzer)){throw 'Single-trace analyzer is missing'}
if($Backend -eq 'Automation' -and -not(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'usb_control_automation.py'))){throw 'Automation CSV adapter is missing'}
$sourceBefore=Snapshot $source
$scriptBefore=Snapshot $script
New-Item -ItemType Directory -Path $out | Out-Null
$work=Join-Path $out 'working.usb'
Copy-Item -LiteralPath $source -Destination $work
Set-ItemProperty -LiteralPath $work -Name IsReadOnly -Value $true
$workBefore=Snapshot $work
if($workBefore.sha256 -ne $sourceBefore.sha256 -or -not $workBefore.readonly){throw 'Protected copy verification failed'}
$exe=$env:LECROY_USB_SUITE_EXE
if(-not $exe){$exe='C:\Program Files\LeCroy\USB Protocol Suite\UsbSuite.exe'}
if(-not(Test-Path -LiteralPath $exe)){throw 'LeCroy executable not found; start from USBTraceTriage.exe to detect its installation'}
Save (Join-Path $out 'before.json') ([ordered]@{source_path=$source;source=$sourceBefore;working=$workBefore;
    script=$scriptBefore;host=Snapshot $hostFile;backend=$Backend;software_version=(Get-Item -LiteralPath $exe).VersionInfo.FileVersion;exe=Snapshot $exe})
$watch=[Diagnostics.Stopwatch]::StartNew()
if($Backend -eq 'Vse'){
    Add-Type -Path $hostFile
    $run=[U01Host]::Run($work,$script,(Join-Path $out 'lifecycle.log'))
}else{
    $app=$null;$trace=$null;$nativeError='';$nativeErrors=@()
    try{
        $app=New-Object -ComObject CATC.UsbTracer
        $trace=$app.OpenFile($work)
        $trace.ExportToCsv((Join-Path $out 'transfers.csv'),3,-1,-1)
        foreach($bit in 0..13){
            $collection=$null
            try{
                $code=[int][Math]::Pow(2,$bit)
                $collection=$trace.AnalyzerErrors($code)
                $nativeErrors+=,[ordered]@{error_type=$code;count=$collection.Count;state='returned'}
            }catch{$nativeErrors+=,[ordered]@{error_type=$code;state='not_available';error=$_.Exception.GetBaseException().Message}}
            finally{if($collection){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($collection)}}
        }
    }catch{$nativeError=$_.Exception.GetBaseException().Message}
    finally{
        if($trace){try{$trace.Close()}catch{$nativeError+=' close: '+$_.Exception.GetBaseException().Message}}
        foreach($value in @($trace,$app)){
            if($value){try{[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($value)}catch{$nativeError+=' release: '+$_.Exception.GetBaseException().Message}}
        }
    }
}
[GC]::Collect();[GC]::WaitForPendingFinalizers();[GC]::Collect()
$watch.Stop()
$sourceAfter=Snapshot $source
$workAfter=Snapshot $work
$integrity=[ordered]@{source_unchanged=(Same $sourceBefore $sourceAfter);working_copy_unchanged=(Same $workBefore $workAfter);working_copy_readonly=($workBefore.readonly -and $workAfter.readonly);script_unchanged=(Same $scriptBefore (Snapshot $script))}
Save (Join-Path $out 'integrity.json') ([ordered]@{checks=$integrity;source_before=$sourceBefore;source_after=$sourceAfter;working_before=$workBefore;working_after=$workAfter})
if($Backend -eq 'Vse'){
    $raw=[ordered]@{trace_sha256=$sourceBefore.sha256;script_sha256=$scriptBefore.sha256;
        run_result=$run.RunResult;finished_result=$run.Sink.FinishedResult;error=$run.Error;
        integrity=$integrity;summary=$run.Sink.Summary;reports=@($run.Sink.Reports.ToArray());extraction_elapsed_ms=$watch.ElapsedMilliseconds}
}else{
    $csvFile=Join-Path $out 'transfers.csv'
    $raw=[ordered]@{adapter='native_transfer_csv';trace_sha256=$sourceBefore.sha256;
        automation_completed=($nativeError -eq '' -and (Test-Path -LiteralPath $csvFile));error=$nativeError;
        csv_sha256=if(Test-Path -LiteralPath $csvFile){(Snapshot $csvFile).sha256}else{$null};
        integrity=$integrity;analyzer_errors=$nativeErrors;extraction_elapsed_ms=$watch.ElapsedMilliseconds}
}
Save (Join-Path $out 'raw-result.json') $raw
if($integrity.Values -contains $false){throw 'Input integrity failed; raw evidence saved, analysis stopped'}
if($Backend -eq 'Vse'){
    & $Python -X utf8 -B $analyzer analyze --input (Join-Path $out 'raw-result.json') --output $out
}else{
    & $Python -X utf8 -B (Join-Path $PSScriptRoot 'usb_control_automation.py') --input (Join-Path $out 'raw-result.json') --output $out
}
if($LASTEXITCODE -ne 0){throw 'Analysis failed; inspect raw-result.json and lifecycle.log'}
