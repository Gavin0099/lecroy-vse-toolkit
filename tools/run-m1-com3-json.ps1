param(
    [Parameter(Mandatory = $true)]
    [string] $TracePath,

    [Parameter(Mandatory = $true)]
    [string] $ScriptPath,

    [Parameter(Mandatory = $false)]
    [string] $OutputPath
)

$ErrorActionPreference = 'Stop'

if (-not $OutputPath) {
    $OutputPath = Join-Path (Split-Path -Parent $TracePath) 'summary.json'
}

$resolvedTracePath = [System.IO.Path]::GetFullPath($TracePath)
$resolvedScriptPath = [System.IO.Path]::GetFullPath($ScriptPath)
$resolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)

if (-not (Test-Path -LiteralPath $resolvedTracePath -PathType Leaf)) {
    throw "Trace does not exist: $resolvedTracePath"
}
if (-not (Test-Path -LiteralPath $resolvedScriptPath -PathType Leaf)) {
    throw "VSE script does not exist: $resolvedScriptPath"
}
if (Test-Path -LiteralPath $resolvedOutputPath) {
    throw "Refusing to overwrite existing output: $resolvedOutputPath"
}

Add-Type -Path (Join-Path $PSScriptRoot 'm1-com2-notify.cs')
$bridge = [M1Com2Runner]::Run($resolvedTracePath, $resolvedScriptPath)

$bridgeAccepted = (
    $bridge.Error -eq '' -and
    $bridge.RunResult -eq 2 -and
    $bridge.NotifyCount -eq 1 -and
    $bridge.EventId -eq 2001 -and
    $bridge.Tag -eq 4242 -and
    $bridge.Marker -eq 'M1-COM2' -and
    $bridge.EventCount -eq 3186175 -and
    $bridge.Usb3RxCount -eq 632512 -and
    $bridge.Usb3TxCount -eq 2553662 -and
    $bridge.UsbCcCount -eq 1 -and
    $bridge.PayloadError -eq ''
)

if (-not $bridgeAccepted) {
    throw "COM2 bridge acceptance failed; refusing to write an artifact. $($bridge | ConvertTo-Json -Compress)"
}

$summary = [ordered]@{
    event_count = [long]$bridge.EventCount
    usb3_rx = [long]$bridge.Usb3RxCount
    usb3_tx = [long]$bridge.Usb3TxCount
    usb_cc = [long]$bridge.UsbCcCount
}

$json = $summary | ConvertTo-Json -Depth 2
[System.IO.File]::WriteAllText(
    $resolvedOutputPath,
    $json + [Environment]::NewLine,
    [System.Text.UTF8Encoding]::new($false)
)

$hostWriteCompleted = Test-Path -LiteralPath $resolvedOutputPath -PathType Leaf
if (-not $hostWriteCompleted) {
    throw "Host write completed without an observable output file: $resolvedOutputPath"
}

$readBack = Get-Content -LiteralPath $resolvedOutputPath -Raw | ConvertFrom-Json
$readBackMatch = (
    [long]$readBack.event_count -eq $summary.event_count -and
    [long]$readBack.usb3_rx -eq $summary.usb3_rx -and
    [long]$readBack.usb3_tx -eq $summary.usb3_tx -and
    [long]$readBack.usb_cc -eq $summary.usb_cc
)

$verification = [ordered]@{
    output_path = $resolvedOutputPath
    summary_json_exists = $hostWriteCompleted
    valid_json = $true
    host_received_notify = $bridge.NotifyCount
    host_write_completed = $hostWriteCompleted
    read_back_match = $readBackMatch
    event_count = [long]$readBack.event_count
    usb3_rx = [long]$readBack.usb3_rx
    usb3_tx = [long]$readBack.usb3_tx
    usb_cc = [long]$readBack.usb_cc
    bridge_run_result = $bridge.RunResult
    bridge_elapsed_milliseconds = $bridge.ElapsedMilliseconds
}

$verification | ConvertTo-Json -Compress
if (-not $readBackMatch) {
    exit 1
}
