param(
    [Parameter(Mandatory = $true)]
    [string] $BeforePath,

    [Parameter(Mandatory = $true)]
    [string] $AfterPath,

    [Parameter(Mandatory = $true)]
    [string] $OutputPath
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $BeforePath -PathType Leaf)) {
    throw "Before trace does not exist: $BeforePath"
}

if (-not (Test-Path -LiteralPath $AfterPath -PathType Leaf)) {
    throw "After trace does not exist: $AfterPath"
}

if (Test-Path -LiteralPath $OutputPath) {
    throw "Refusing to overwrite existing output: $OutputPath"
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory -and -not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

Add-Type -Path (Join-Path $PSScriptRoot 'trace-mutation-localizer.cs')
$report = [TraceMutationLocalizer]::Compare($BeforePath, $AfterPath)
$json = $report | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText(
    $OutputPath,
    $json + [Environment]::NewLine,
    [System.Text.UTF8Encoding]::new($false)
)

$readBack = Get-Content -LiteralPath $OutputPath -Raw | ConvertFrom-Json
[pscustomobject]@{
    output_path = $OutputPath
    before_size = $readBack.BeforeSize
    after_size = $readBack.AfterSize
    size_delta = $readBack.SizeDelta
    first_differing_offset = $readBack.FirstDifferingOffset
    last_differing_offset = $readBack.LastDifferingOffset
    changed_byte_count = $readBack.ChangedByteCount
    range_count = $readBack.Ranges.Count
    ranges = ($readBack.Ranges | ConvertTo-Json -Compress)
} | ConvertTo-Json -Compress
