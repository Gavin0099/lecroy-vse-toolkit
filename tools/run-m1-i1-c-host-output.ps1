param(
    [Parameter(Mandatory = $true)]
    [string] $TracePath,

    [Parameter(Mandatory = $true)]
    [string] $ScriptPath,

    [Parameter(Mandatory = $true)]
    [string] $OutputPath
)

$ErrorActionPreference = 'Stop'
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
$outputDirectory = Split-Path -Parent $resolvedOutputPath
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

Add-Type -Path @(
    (Join-Path $PSScriptRoot 'm1-com2-notify.cs'),
    (Join-Path $PSScriptRoot 'm1-i1-stage-c.cs')
)
$result = [M1I1StageCRunner]::Run($resolvedTracePath, $resolvedScriptPath, $resolvedOutputPath)

$readBackMatch = $false
if ($result.HostWriteCompleted -and (Test-Path -LiteralPath $resolvedOutputPath -PathType Leaf)) {
    $readBack = Get-Content -LiteralPath $resolvedOutputPath -Raw | ConvertFrom-Json
    $readBackMatch = (
        [long]$readBack.event_count -eq $result.EventCount -and
        [long]$readBack.usb3_rx -eq $result.Usb3RxCount -and
        [long]$readBack.usb3_tx -eq $result.Usb3TxCount -and
        [long]$readBack.usb_cc -eq $result.UsbCcCount
    )
}

$verification = [ordered]@{
    output_path = $resolvedOutputPath
    run_result = $result.RunResult
    elapsed_milliseconds = $result.ElapsedMilliseconds
    notify_count = $result.NotifyCount
    event_id = $result.EventId
    tag = $result.Tag
    marker = $result.Marker
    event_count = $result.EventCount
    usb3_rx = $result.Usb3RxCount
    usb3_tx = $result.Usb3TxCount
    usb_cc = $result.UsbCcCount
    host_write_completed = $result.HostWriteCompleted
    read_back_match = $readBackMatch
    error = $result.Error
}
$verification | ConvertTo-Json -Compress

$accepted = (
    $result.Error -eq '' -and
    $result.RunResult -eq 2 -and
    $result.NotifyCount -eq 1 -and
    $result.EventId -eq 2001 -and
    $result.Tag -eq 4242 -and
    $result.Marker -eq 'M1-COM2' -and
    $result.EventCount -eq 3186175 -and
    $result.Usb3RxCount -eq 632512 -and
    $result.Usb3TxCount -eq 2553662 -and
    $result.UsbCcCount -eq 1 -and
    $result.PayloadError -eq '' -and
    $result.HostWriteCompleted -and
    $readBackMatch
)
if (-not $accepted) {
    exit 1
}
