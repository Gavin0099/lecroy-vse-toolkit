param(
    [Parameter(Mandatory = $true)]
    [string] $TracePath
)

$ErrorActionPreference = 'Stop'
$resolvedTracePath = [System.IO.Path]::GetFullPath($TracePath)
if (-not (Test-Path -LiteralPath $resolvedTracePath -PathType Leaf)) {
    throw "Trace does not exist: $resolvedTracePath"
}

Add-Type -Path (Join-Path $PSScriptRoot 'm1-i1-open-close.cs')
$result = [M1I1OpenCloseRunner]::Run($resolvedTracePath)
$result | ConvertTo-Json -Compress

if ($result.Error -or -not $result.OpenSucceeded -or -not $result.CloseSucceeded) {
    exit 1
}
