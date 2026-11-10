<#
.SYNOPSIS
  Extracts FMUpgradeTool and FMDeveloperTool from the FileMaker Server .msi, without installing it.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\extract-fms-tools.ps1 -Msi "C:\Downloads\FileMaker Server 26.msi"
#>
param(
  [Parameter(Mandatory = $true)][string]$Msi,
  [string]$Destination = (Join-Path $env:LOCALAPPDATA "patchwork\fms-tools")
)

$ErrorActionPreference = "Stop"
$Msi = (Resolve-Path $Msi).Path
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$log = Join-Path $Destination "extract.log"

Write-Output "Extracting $Msi"
Write-Output "        to $Destination (administrative install: nothing is registered or started)"
$process = Start-Process msiexec.exe -ArgumentList "/a `"$Msi`" TARGETDIR=`"$Destination`" /qn /l*v `"$log`"" -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "msiexec failed with exit code $($process.ExitCode). See $log" }

$tool = Get-ChildItem $Destination -Recurse -Filter "FMUpgradeTool.exe" | Select-Object -First 1
if (-not $tool) { throw "FMUpgradeTool.exe was not found in the extracted files. See $log" }

Write-Output ""
Write-Output "Found $($tool.FullName)"
Write-Output "Run: patchwork doctor"
