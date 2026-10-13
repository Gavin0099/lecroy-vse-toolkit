$ErrorActionPreference='Stop'
$repo=Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$dest=Join-Path $PSScriptRoot 'u02-raw-packets'
if(Test-Path -LiteralPath $dest){throw 'Refuse overwrite'}
New-Item -ItemType Directory -Path $dest | Out-Null
$source=Join-Path $repo 'dp1 hub detect SSD fail-2.usb'
$work=Join-Path $dest 'working.usb'
$before=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
Copy-Item -LiteralPath $source -Destination $work
Set-ItemProperty -LiteralPath $work -Name IsReadOnly -Value $true
Add-Type -Path (Join-Path $repo 'tools/u01-selection-host.cs')
$type=[type]::GetTypeFromProgID('CATC.UsbTracer')
$analyzer=[U01Host]::Activate([Func[object]]{[Activator]::CreateInstance($type)},$null)
$trace=$null
$records=@()
try {
    $trace=$analyzer.OpenFile($work)
    foreach($number in @(8,9)) {
        $packet=$null
        $bits=$trace.GetPacket($number,[ref]$packet)
        if(@($packet).Count -gt 256 -or $bits -lt 0 -or $bits -gt 8*@($packet).Count){throw 'Raw packet bounds invalid'}
        $records+=[ordered]@{index=$number;number_of_bits=$bits;bytes=@($packet | ForEach-Object {[int]$_});hex=(@($packet | ForEach-Object {'{0:X2}' -f [int]$_}) -join ' ')}
    }
} finally {
    if($trace){$trace.Close();[Runtime.InteropServices.Marshal]::FinalReleaseComObject($trace) | Out-Null}
    [Runtime.InteropServices.Marshal]::FinalReleaseComObject($analyzer) | Out-Null
}
$sourceAfter=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
$workAfter=(Get-FileHash -LiteralPath $work -Algorithm SHA256).Hash
$record=[ordered]@{trace_sha256=$before;source_unchanged=($before -eq $sourceAfter);working_unchanged=($before -eq $workAfter);working_readonly=(Get-Item -LiteralPath $work).IsReadOnly;packet_records=$records;wire_layout_verified=$false;crc_correctness='NOT_EVALUATED'}
$record | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath (Join-Path $dest 'raw.json') -Encoding UTF8
if(-not $record.source_unchanged -or -not $record.working_unchanged -or -not $record.working_readonly){throw 'Raw reference integrity changed'}
$record | ConvertTo-Json -Depth 9
