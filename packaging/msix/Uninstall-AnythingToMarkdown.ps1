<#
.SYNOPSIS
    Remove the AnythingToMarkdown MSIX package from this machine.

.DESCRIPTION
    An MSIX already uninstalls cleanly without any script — this is the same
    operation, scripted, for automation and for tidying up test installs:

        Start menu  ->  right-click AnythingToMarkdown  ->  Uninstall
        Settings    ->  Apps  ->  Installed apps  ->  AnythingToMarkdown  ->  Uninstall

    Either route removes the whole package: the executable, every bundled
    dependency, the Start menu entry, the file type associations, the
    `anytomd` command alias and the app's private data folder. MSIX installs
    do not touch the registry or Program Files, so nothing is left behind.
    Markdown files the app produced are ordinary user documents and are never
    deleted.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\msix\Uninstall-AnythingToMarkdown.ps1

.EXAMPLE
    # Also drop the self-signed test certificate that was trusted for sideloading.
    powershell -File packaging\msix\Uninstall-AnythingToMarkdown.ps1 -RemoveTestCertificate
#>
[CmdletBinding()]
param(
    # Package family/identity name. Override if you reserved a different name.
    [string]$PackageName,

    # Remove the sideloading test certificate from LocalMachine\TrustedPeople
    # (needs an elevated PowerShell).
    [switch]$RemoveTestCertificate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $PackageName) {
    if ($env:MSIX_IDENTITY_NAME) {
        $PackageName = $env:MSIX_IDENTITY_NAME
    } else {
        # Same source of truth the package was built from.
        $identityFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "identity.json"
        $PackageName = (Get-Content $identityFile -Raw | ConvertFrom-Json).identityName
    }
}

$packages = @(Get-AppxPackage -Name $PackageName -ErrorAction SilentlyContinue)
if ($packages.Count -eq 0) {
    Write-Host "$PackageName is not installed for the current user — nothing to do."
} else {
    foreach ($pkg in $packages) {
        Write-Host "Removing $($pkg.PackageFullName)"
        Remove-AppxPackage -Package $pkg.PackageFullName
    }
    Write-Host "Uninstalled $PackageName."
}

if ($RemoveTestCertificate) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Warning "Removing the test certificate needs an elevated PowerShell — skipped."
    } else {
        $certs = @(Get-ChildItem Cert:\LocalMachine\TrustedPeople -ErrorAction SilentlyContinue |
            Where-Object { $_.FriendlyName -eq "AnythingToMarkdown MSIX test certificate" })
        foreach ($c in $certs) {
            Remove-Item $c.PSPath -Force
            Write-Host "Removed test certificate $($c.Thumbprint)"
        }
        if ($certs.Count -eq 0) { Write-Host "No AnythingToMarkdown test certificate found." }
    }
}
