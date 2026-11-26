$ErrorActionPreference='Stop'
$repo=Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$dest=Join-Path $PSScriptRoot 'u04-discovery'
if(Test-Path -LiteralPath $dest){throw 'Refuse overwrite'}
New-Item -ItemType Directory -Path $dest | Out-Null
$saved=Get-Content -LiteralPath (Join-Path $repo 'c4-demo-regression-20260911/fail-timeline.json') -Raw | ConvertFrom-Json
$events=@($saved.events | Where-Object {$_.EventClass -eq 'LTSSM_STATE'} | Select-Object -First 3)
if($events.Count -eq 0){throw 'No saved LTSSM event candidates'}
$source=Join-Path $repo 'dp1 hub detect SSD fail-2.usb'
$hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if($hash -ne $saved.before.sha256){throw 'Saved trace identity mismatch'}
$work=Join-Path $dest 'working.usb'
Copy-Item -LiteralPath $source -Destination $work
Set-ItemProperty -LiteralPath $work -Name IsReadOnly -Value $true
Add-Type -Path (Join-Path $repo 'tools/u01-selection-host.cs')
$type=[type]::GetTypeFromProgID('CATC.UsbTracer')
$analyzer=[U01Host]::Activate([Func[object]]{[Activator]::CreateInstance($type)},$null)
$trace=$null
try {
    $trace=$analyzer.OpenFile($work)
    foreach($e in $events){
        $out=Join-Path $dest ('packet-'+$e.Index+'.txt')
        $trace.ExportToText($out,[int]$e.Index,[int]$e.Index)
        if(-not(Test-Path -LiteralPath $out)){throw 'No export file'}
    }
} finally {
    if($trace){$trace.Close();[Runtime.InteropServices.Marshal]::FinalReleaseComObject($trace) | Out-Null}
    [Runtime.InteropServices.Marshal]::FinalReleaseComObject($analyzer) | Out-Null
}
$record=[ordered]@{trace_sha256=$hash;saved_ltssm_candidates=$events;source_unchanged=($hash -eq (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash);working_unchanged=($hash -eq (Get-FileHash -LiteralPath $work -Algorithm SHA256).Hash);working_readonly=(Get-Item -LiteralPath $work).IsReadOnly;export_method='ExportToText explicit single packet range; display filters not independently known';qualification='NOT_EVALUATED'}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $dest 'discovery.json') -Encoding UTF8
if(-not $record.source_unchanged -or -not $record.working_unchanged -or -not $record.working_readonly){throw 'Discovery integrity failed'}
Get-ChildItem -LiteralPath $dest -Filter '*.txt' | ForEach-Object {Get-Content -LiteralPath $_.FullName -TotalCount 45}
