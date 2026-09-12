<#
.SYNOPSIS
    Install a locally built AnythingToMarkdown .msix on this machine.

.DESCRIPTION
    Only needed for testing a package before it goes to the Store. Users who
    install from the Microsoft Store never run this.

    Windows refuses to install an MSIX unless it is signed by a certificate the
    machine trusts, so if the package was built with -SelfSign this script
    first imports the accompanying .cer into LocalMachine\TrustedPeople. That
    step requires an elevated PowerShell; the install itself does not.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\msix\Install-Sideload.ps1

.EXAMPLE
    powershell -File packaging\msix\Install-Sideload.ps1 -MsixPath dist\AnythingToMarkdown-1.0.0.0-x64.msix
#>
[CmdletBinding()]
param(
    # Defaults to the newest .msix in dist\.
    [string]$MsixPath,

    # Public certificate to trust. Defaults to the .cer next to the package.
    [string]$CertificatePath,

    # Skip importing the certificate (it is already trusted, or the package is
    # signed by a publicly trusted CA).
    [switch]$SkipCertificate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..\..")

if (-not $MsixPath) {
    $candidate = Get-ChildItem (Join-Path $Root "dist") -Filter "*.msix" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $candidate) {
        throw "No .msix found in dist\. Build one first: packaging\msix\build_msix.ps1 -SelfSign"
    }
    $MsixPath = $candidate.FullName
}
if (-not (Test-Path $MsixPath)) { throw "Package not found: $MsixPath" }
Write-Host "Package: $MsixPath"

if (-not $SkipCertificate) {
    if (-not $CertificatePath) {
        $CertificatePath = Join-Path (Split-Path -Parent $MsixPath) "AnythingToMarkdown-test.cer"
    }
    if (Test-Path $CertificatePath) {
        $isAdmin = ([Security.Principal.WindowsPrincipal] `
            [Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

        if (-not $isAdmin) {
            throw "Trusting $CertificatePath needs an elevated PowerShell. Re-run this script as Administrator, or pass -SkipCertificate if the certificate is already trusted."
        }
        Import-Certificate -FilePath $CertificatePath `
            -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null
        Write-Host "Trusted certificate: $CertificatePath"
    } else {
        Write-Host "No .cer alongside the package — assuming it is already signed by a trusted certificate."
    }
}

Add-AppxPackage -Path $MsixPath
Write-Host ""
Write-Host "Installed. Find 'AnythingToMarkdown' in the Start menu."
Write-Host "Uninstall with: packaging\msix\Uninstall-AnythingToMarkdown.ps1"
