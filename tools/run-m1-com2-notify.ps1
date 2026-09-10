param(
    [Parameter(Mandatory = $true)]
    [string] $TracePath,

    [Parameter(Mandatory = $true)]
    [string] $ScriptPath
)

$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'm1-com2-notify.cs')
$result = [M1Com2Runner]::Run($TracePath, $ScriptPath)
$result | ConvertTo-Json -Compress

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
    $result.PayloadError -eq ''
)

if (-not $accepted) {
    exit 1
}
