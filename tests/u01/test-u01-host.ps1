# Offline managed callback replay only. This script never invokes U01Host.Run.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Add-Type -Path (Join-Path $root 'tools/u01-selection-host.cs')
function Assert([bool]$condition,[string]$message) { if (-not $condition) { throw $message } }
$sink = [U01Sink]::new()
$sink.OnNotifyClient(2501, [object[]]@('U01-ROW',10,0,5,4,300,1,2,-1),0)
$sink.OnNotifyClient(2502, [object[]]@('U01-END',17,1,1,0,0),0)
$sink.OnVScriptFinished('synthetic.vse',2,0)
Assert ($sink.Rows.Count -eq 1 -and $sink.Rows[0][0] -eq 10 -and $sink.Summary[0] -eq 17 -and $sink.Error -eq '') 'handwritten managed replay mismatch'
$sink.OnNotifyClient(2501, [object[]]@('U01-ROW',20,0,5,4,300,1,3,-1),0)
Assert ($sink.Error -match 'after end') 'row after end was accepted'
$sink = [U01Sink]::new()
$sink.OnNotifyClient(2502, [object[]]@('U01-END',0,0,0,0,0),0)
$sink.OnNotifyClient(2502, [object[]]@('U01-END',0,0,0,0,0),0)
Assert ($sink.Error -match 'duplicate') 'duplicate end was accepted'
foreach ($body in @(@('U01-ROW','10',0,5,4,300,1,2,-1), @('WRONG',10,0,5,4,300,1,2,-1), @('U01-ROW',$true,0,5,4,300,1,2,-1))) {
    $sink = [U01Sink]::new(); $sink.OnNotifyClient(2501,[object[]]$body,0)
    Assert ($sink.Error -ne '') 'malformed callback was accepted'
}
$sink = [U01Sink]::new()
$sink.OnNotifyClient(2501,[object[]]@('U01-ROW',10,0,5,4,300,1,2,'NOT_APPLICABLE'),0)
Assert ($sink.Error -eq '' -and $sink.Rows[0][7] -eq -1) 'explicit NA token did not retain inapplicable sentinel'
$sink = [U01Sink]::new()
$sink.OnNotifyClient(2501,[object[]]@('U01-ROW',10,0,5,4,300,1,2,'unknown'),0)
Assert ($sink.Error -ne '') 'unknown token was silently coerced to NA'
$script:u01Attempts=0
$creator=[Func[object]]{
    $script:u01Attempts++
    if ($script:u01Attempts -eq 1) { throw [Runtime.InteropServices.COMException]::new('synthetic class factory RPC failure',-2147023169) }
    return 'factory-created'
}
$created=[U01Host]::Activate($creator,$null)
Assert ($created -eq 'factory-created' -and $script:u01Attempts -eq 2) 'bounded activation recovery did not return the created object'
$script:u01Attempts=0
$creator=[Func[object]]{ $script:u01Attempts++; throw [Runtime.InteropServices.COMException]::new('unrelated failure',-2147467259) }
$caught=$false
try {[U01Host]::Activate($creator,$null) | Out-Null} catch {$caught=$true}
Assert ($caught -and $script:u01Attempts -eq 1) 'unrelated activation failure was hidden or retried'
$tokens=$null; $parseErrors=$null
[Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'tools/run-u01-selection.ps1'),[ref]$tokens,[ref]$parseErrors) | Out-Null
Assert ($parseErrors.Count -eq 0) 'runner PowerShell syntax failed'
Write-Output 'PASS: C# compiled; 8 managed callback cases; 2 activation recovery cases; runner parsed; no COM activation.'
