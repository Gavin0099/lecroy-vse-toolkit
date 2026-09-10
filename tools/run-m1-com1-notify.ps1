param(
    [Parameter(Mandatory = $true)]
    [string] $TracePath,

    [Parameter(Mandatory = $true)]
    [string] $ScriptPath
)

$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'm1-com1-notify.cs')
$result = [M1Com1Runner]::Run($TracePath, $ScriptPath)
$result | ConvertTo-Json -Compress
if ($result.Error) {
    exit 1
}
