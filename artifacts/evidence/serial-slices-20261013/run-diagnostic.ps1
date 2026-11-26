param([string]$Name='u01-diagnostic-1', [string]$Script='diagnostic.vse')
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$dest=Join-Path $PSScriptRoot $Name
if (Test-Path -LiteralPath $dest) {throw 'Refuse overwrite'}
New-Item -ItemType Directory -Path $dest | Out-Null
$source=Join-Path $repo 'dp1 hub detect SSD fail-2.usb'
$work=Join-Path $dest 'working.usb'
$expected=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
Copy-Item -LiteralPath $source -Destination $work
Set-ItemProperty -LiteralPath $work -Name IsReadOnly -Value $true
if ((Get-FileHash -LiteralPath $work -Algorithm SHA256).Hash -ne $expected) {throw 'Copy mismatch'}
Add-Type -Path (Join-Path $repo 'tools/u01-selection-host.cs')
$scriptFile=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot $Script)).Path
$before=[ordered]@{source_hash=$expected;work_hash=$expected;script_hash=(Get-FileHash -LiteralPath $scriptFile -Algorithm SHA256).Hash;work_readonly=(Get-Item -LiteralPath $work).IsReadOnly}
$before | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dest 'before.json') -Encoding UTF8
$r=[U01Host]::Run($work,$scriptFile,(Join-Path $dest 'lifecycle.log'))
$state=[ordered]@{run_result=$r.RunResult;error=$r.Error;reports=@($r.Sink.Reports.ToArray());finished=$r.Sink.FinishedResult;source_hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash;working_hash=(Get-FileHash -LiteralPath $work -Algorithm SHA256).Hash;working_readonly=(Get-Item -LiteralPath $work).IsReadOnly;qualification='NOT_EVALUATED'}
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $dest 'result.json') -Encoding UTF8
$state | ConvertTo-Json -Depth 8
