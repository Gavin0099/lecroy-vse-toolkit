[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$SessionDirectory)
$ErrorActionPreference='Stop'
if([Threading.Thread]::CurrentThread.ApartmentState -ne 'STA'){throw 'Navigation requires STA'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Web.Extensions
Add-Type -Path (Join-Path $PSScriptRoot 'usb-control-navigation.cs') -ReferencedAssemblies System.Windows.Forms,System.Web.Extensions,System.Drawing,System.Core
[TraceNavigationWorker]::Run([IO.Path]::GetFullPath($SessionDirectory))
