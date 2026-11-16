$ErrorActionPreference='Stop'
$repo=Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$dest=Join-Path $PSScriptRoot 'u05-discovery'
if(Test-Path -LiteralPath $dest){throw 'Refuse overwrite'}
New-Item -ItemType Directory -Path $dest | Out-Null
$source=Join-Path $repo 'dp1 hub detect SSD fail-2.usb'
$hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
$work=Join-Path $dest 'working.usb'
Copy-Item -LiteralPath $source -Destination $work
Set-ItemProperty -LiteralPath $work -Name IsReadOnly -Value $true
Add-Type -Path (Join-Path $repo 'tools/u01-selection-host.cs')
$type=[type]::GetTypeFromProgID('CATC.UsbTracer')
$analyzer=[U01Host]::Activate([Func[object]]{[Activator]::CreateInstance($type)},$null)
$trace=$null
try {
    $trace=$analyzer.OpenFile($work)
    # LC-05 IUsbTrace2 ExportToCsv, PDF132-134: 1=USB transactions, 3=transfers.
    $trace.ExportToCsv((Join-Path $dest 'transactions.csv'),1,0,2)
    $trace.ExportToCsv((Join-Path $dest 'transfers.csv'),3,0,2)
} finally {
    if($trace){$trace.Close();[Runtime.InteropServices.Marshal]::FinalReleaseComObject($trace) | Out-Null}
    [Runtime.InteropServices.Marshal]::FinalReleaseComObject($analyzer) | Out-Null
}
$record=[ordered]@{trace_sha256=$hash;source_unchanged=($hash -eq (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash);working_unchanged=($hash -eq (Get-FileHash -LiteralPath $work -Algorithm SHA256).Hash);working_readonly=(Get-Item -LiteralPath $work).IsReadOnly;method='ExportToCsv levels1/3, native unit indices0..2; filters/effective range not independently verified';qualification='NOT_EVALUATED'}
$record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dest 'discovery.json') -Encoding UTF8
if(-not $record.source_unchanged -or -not $record.working_unchanged -or -not $record.working_readonly){throw 'Discovery integrity failed'}
Get-ChildItem -LiteralPath $dest -Filter '*.csv' | ForEach-Object {Get-Content -LiteralPath $_.FullName -TotalCount 15}
