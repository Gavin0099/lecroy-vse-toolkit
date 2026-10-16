[CmdletBinding()]
param([string]$Python='python',[string]$Output)
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME 'Modules'
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Web.Extensions
    $packaged=Join-Path $PSScriptRoot '..\USBTraceTriage.exe'
    if(Test-Path -LiteralPath $packaged){
        $entryProcess=Start-Process -FilePath $packaged -PassThru
        $entryProcess.WaitForExit()
        exit $entryProcess.ExitCode
    }
    $pythonCommand=Get-Command $Python -ErrorAction Stop
    $pythonPath=$pythonCommand.Source
    if(-not $pythonPath){throw 'Python executable not found'}
    if($pythonPath -like '*\Microsoft\WindowsApps\*'){throw 'Install actual Python 3.10+; a Windows Store alias is not a runtime'}
    & $pythonPath -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10 or later required"'
    if($LASTEXITCODE -ne 0){throw 'Python 3.10 or later is required'}
    if(-not [Type]::GetTypeFromProgID('CATC.UsbTracer')){throw 'LeCroy COM registration is missing'}
    if(-not $Output){
        $parent=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'LeCroyTraceTriage'
        [IO.Directory]::CreateDirectory($parent) | Out-Null
        $Output=Join-Path $parent ('run-'+[DateTime]::Now.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
    }
    if(Test-Path -LiteralPath $Output){throw 'Use a new output directory; previous results are not overwritten'}
    $entrySource=Join-Path $PSScriptRoot 'usb-control-entry.cs'
    $code=([IO.File]::ReadAllText($entrySource))+[Environment]::NewLine+([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'usb-control-startup.cs')))+[Environment]::NewLine+([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'usb-control-theme.cs')))
    # Add-Type requires using directives before type declarations; compile files together.
    $hash=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($code)))).Replace('-','').Substring(0,16)
    $cache=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) ('LeCroyTraceTriage\bin\'+$hash)
    [IO.Directory]::CreateDirectory($cache) | Out-Null
    $entry=Join-Path $cache 'USBTraceTriage.exe'
    if(-not(Test-Path -LiteralPath $entry)){
        Add-Type -Path @($entrySource,(Join-Path $PSScriptRoot 'usb-control-startup.cs'),(Join-Path $PSScriptRoot 'usb-control-theme.cs')) -OutputAssembly $entry -OutputType WindowsApplication -ReferencedAssemblies System.Windows.Forms,System.Web.Extensions,System.Drawing,System.Core
    }
    $assembly=[Reflection.Assembly]::LoadFile($entry)
    $entryType=$assembly.GetType('TraceToolEntry')
    $startupType=$assembly.GetType('TraceStartup')
    $analyzer=$startupType.GetMethod('FindAnalyzer').Invoke($null,@())
    if(-not $analyzer){
        $picker=[Windows.Forms.OpenFileDialog]::new()
        $picker.Filter='LeCroy USB Protocol Suite|UsbSuite.exe'
        if($picker.ShowDialog() -ne [Windows.Forms.DialogResult]::OK){throw 'LeCroy installation was not specified'}
        $analyzer=$picker.FileName
    }
    $startupType.GetMethod('ValidateAnalyzer').Invoke($null,@([string]$analyzer))
    $env:LECROY_USB_SUITE_EXE=$analyzer
    $quoted=@($pythonPath,(Join-Path $PSScriptRoot 'usb_control_app.py'),[IO.Path]::GetFullPath($Output)) | ForEach-Object {$entryType.GetMethod('Quote').Invoke($null,@([string]$_))}
    $info=[Diagnostics.ProcessStartInfo]::new($entry,($quoted -join ' '))
    $info.UseShellExecute=$false
    $process=[Diagnostics.Process]::Start($info)
    $process.WaitForExit()
    if($process.ExitCode -ne 0){throw 'Native entry did not complete normally'}
} catch {
    $startupError='Unable to start Trace Triage source checkout. Use the portable ZIP with bundled Python, or install Python 3.10+, Windows PowerShell 5.1/.NET Framework and registered LeCroy USB Protocol Suite. Details: '+$_.Exception.GetBaseException().Message
    try{[System.Windows.Forms.MessageBox]::Show($startupError,'USB Trace Triage') | Out-Null}catch{Write-Error $startupError}
    exit 1
}
