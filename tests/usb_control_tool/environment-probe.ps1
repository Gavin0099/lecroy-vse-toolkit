param([Parameter(Mandatory=$true)][string]$InputPath)
$ErrorActionPreference='Stop'
@{module=(Get-Command Get-FileHash).Source;sha256=(Get-FileHash -LiteralPath $InputPath -Algorithm SHA256).Hash.ToLowerInvariant();edition=$PSVersionTable.PSEdition} | ConvertTo-Json -Compress
