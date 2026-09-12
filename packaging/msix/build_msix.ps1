<#
.SYNOPSIS
    Pack the built AnythingToMarkdown app into an MSIX installer.

.DESCRIPTION
    Takes the one-folder PyInstaller output (BUILD_ONEDIR=1) and turns it into
    a signed or unsigned .msix:

        1. stage the payload + Assets + a filled-in AppxManifest.xml
        2. build resources.pri so Windows can resolve the scale-qualified tiles
        3. makeappx pack
        4. optionally sign (self-signed for local testing, or a real cert)

    Packages destined for the Microsoft Store are uploaded UNSIGNED — Partner
    Center re-signs them with the Store certificate. Sideloaded packages must
    be signed by a certificate the machine trusts, which is what -SelfSign is
    for during development.

.EXAMPLE
    # Store upload (unsigned, revision must be 0)
    powershell -File packaging\msix\build_msix.ps1

.EXAMPLE
    # Local install test
    powershell -File packaging\msix\build_msix.ps1 -SelfSign
#>
[CmdletBinding()]
param(
    # Four-part MSIX version. Defaults to anytomd.__version__ + ".0".
    [string]$Version,

    # One-folder PyInstaller output containing AnythingToMarkdown.exe.
    [string]$Payload,

    # Where the .msix is written.
    [string]$OutDir,

    # Must match Partner Center > Product identity > Package/Identity/Name.
    [string]$IdentityName,

    # Must match Partner Center > Product identity > Publisher (CN=...).
    [string]$Publisher,

    # Must match Partner Center > Product identity > Publisher display name.
    [string]$PublisherDisplayName,

    # Defaults to displayName in identity.json.
    [string]$DisplayName,

    # Sign with an existing .pfx.
    [string]$CertificatePath,
    [string]$CertificatePassword,

    # Generate a throwaway certificate and sign with it (local testing only).
    [switch]$SelfSign
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..\..")

# ---------------------------------------------------------------------------
# Identity resolution, in order of precedence:
#   1. an explicit -IdentityName / -Publisher / ... parameter
#   2. the MSIX_* environment variables (how a fork overrides it in CI)
#   3. packaging/msix/identity.json — this product's Partner Center values
# ---------------------------------------------------------------------------
function Coalesce([string]$a, [string]$b, [string]$c) {
    foreach ($v in @($a, $b, $c)) { if ($v) { return $v } }
    return $null
}

$identityFile = Join-Path $ScriptDir "identity.json"
if (-not (Test-Path $identityFile)) { throw "Missing $identityFile" }
$identity = Get-Content $identityFile -Raw | ConvertFrom-Json

# Read properties defensively: under Set-StrictMode a missing one would throw
# before the clear "check identity.json" message below could fire.
function Get-IdentityField([string]$name) {
    $prop = $identity.PSObject.Properties[$name]
    if ($prop) { return [string]$prop.Value }
    return $null
}

$IdentityName = Coalesce $IdentityName $env:MSIX_IDENTITY_NAME (Get-IdentityField "identityName")
$Publisher = Coalesce $Publisher $env:MSIX_PUBLISHER (Get-IdentityField "publisher")
$PublisherDisplayName = Coalesce $PublisherDisplayName $env:MSIX_PUBLISHER_DISPLAY_NAME (Get-IdentityField "publisherDisplayName")
if (-not $PSBoundParameters.ContainsKey("DisplayName")) {
    $DisplayName = Coalesce $DisplayName (Get-IdentityField "displayName") "AnythingToMarkdown"
}
$Payload = Coalesce $Payload $env:MSIX_PAYLOAD (Join-Path $Root "dist\AnythingToMarkdown")
$OutDir = Coalesce $OutDir $env:MSIX_OUTDIR (Join-Path $Root "dist")

foreach ($pair in @(
    @{ Name = "Identity/Name"; Value = $IdentityName },
    @{ Name = "Identity/Publisher"; Value = $Publisher },
    @{ Name = "PublisherDisplayName"; Value = $PublisherDisplayName }
)) {
    if (-not $pair.Value) { throw "$($pair.Name) resolved to nothing — check $identityFile" }
}
if ($Publisher -notmatch '^CN=') {
    throw "Publisher must be a distinguished name starting with 'CN=', got '$Publisher'."
}

if (-not $Version) {
    $python = Coalesce $env:PYTHON_EXE (Join-Path $Root ".venv\Scripts\python.exe") "python"
    if (-not (Test-Path $python)) { $python = "python" }
    $Version = (& $python (Join-Path $Root "packaging\version_tool.py") msix --revision 0).Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    throw "Version '$Version' must be four numeric parts (MAJOR.MINOR.BUILD.REVISION)."
}

Write-Host "=== AnythingToMarkdown MSIX ==="
Write-Host "  Version   : $Version"
Write-Host "  Identity  : $IdentityName"
Write-Host "  Publisher : $Publisher"
Write-Host "  Payload   : $Payload"

if (-not (Test-Path $Payload)) {
    throw "Payload folder not found: $Payload`nBuild it first with BUILD_ONEDIR=1 pyinstaller packaging\AnythingToMarkdown.spec"
}
$exePath = Join-Path $Payload "AnythingToMarkdown.exe"
if (-not (Test-Path $exePath)) {
    throw "AnythingToMarkdown.exe not found in $Payload — the manifest's Executable would dangle."
}

# Make every path absolute before use. .NET APIs like [File]::WriteAllText
# resolve relative paths against the process working directory, which is not
# necessarily PowerShell's current location — so "dist" could land elsewhere.
$Payload = (Resolve-Path $Payload).Path
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$OutDir = (Resolve-Path $OutDir).Path

# ---------------------------------------------------------------------------
# Locate the Windows SDK packaging tools.
# ---------------------------------------------------------------------------
function Find-SdkTool([string]$Name) {
    $roots = @(
        (Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"),
        (Join-Path $env:ProgramFiles "Windows Kits\10\bin")
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($root in $roots) {
        # Newest SDK first: bin\10.0.22621.0\x64\makeappx.exe
        $versions = @(Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^\d+\.\d+\.\d+\.\d+$' } |
            Sort-Object { [version]$_.Name } -Descending)
        foreach ($v in $versions) {
            foreach ($arch in @("x64", "x86")) {
                $candidate = Join-Path $v.FullName "$arch\$Name"
                if (Test-Path $candidate) { return $candidate }
            }
        }
        # Older SDK layout: bin\x64\makeappx.exe
        foreach ($arch in @("x64", "x86")) {
            $candidate = Join-Path $root "$arch\$Name"
            if (Test-Path $candidate) { return $candidate }
        }
    }

    $onPath = Get-Command $Name -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    return $null
}

$makeappx = Find-SdkTool "makeappx.exe"
if (-not $makeappx) {
    throw "makeappx.exe not found. Install the Windows 10/11 SDK (the 'Windows SDK Signing Tools for Desktop Apps' component)."
}
$makepri = Find-SdkTool "makepri.exe"
$signtool = Find-SdkTool "signtool.exe"
Write-Host "  makeappx  : $makeappx"

# ---------------------------------------------------------------------------
# Stage the package contents.
# ---------------------------------------------------------------------------
$stage = Join-Path $OutDir "msix-stage"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage -Force | Out-Null

Write-Host "Staging payload -> $stage"
Copy-Item (Join-Path $Payload "*") -Destination $stage -Recurse -Force

$assets = Join-Path $ScriptDir "Assets"
if (-not (Test-Path $assets)) {
    throw "Assets folder missing. Run: python packaging\msix\make_msix_assets.py"
}
Copy-Item $assets -Destination $stage -Recurse -Force

# Fill in the manifest placeholders.
function Escape-Xml([string]$s) {
    return $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;')
}

$manifestText = Get-Content (Join-Path $ScriptDir "AppxManifest.xml") -Raw
$manifestText = $manifestText.Replace("{{VERSION}}", (Escape-Xml $Version))
$manifestText = $manifestText.Replace("{{IDENTITY_NAME}}", (Escape-Xml $IdentityName))
$manifestText = $manifestText.Replace("{{PUBLISHER}}", (Escape-Xml $Publisher))
$manifestText = $manifestText.Replace("{{PUBLISHER_DISPLAY_NAME}}", (Escape-Xml $PublisherDisplayName))
$manifestText = $manifestText.Replace("{{DISPLAY_NAME}}", (Escape-Xml $DisplayName))

if ($manifestText -match '\{\{[A-Z_]+\}\}') {
    throw "Unsubstituted placeholder left in AppxManifest.xml: $($Matches[0])"
}

$manifestPath = Join-Path $stage "AppxManifest.xml"
[System.IO.File]::WriteAllText($manifestPath, $manifestText, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Wrote $manifestPath"

# ---------------------------------------------------------------------------
# resources.pri — maps the scale-/targetsize-qualified asset filenames to the
# logical names the manifest references. Without it Windows shows blank tiles.
# ---------------------------------------------------------------------------
if ($makepri) {
    $priConfig = Join-Path $OutDir "priconfig.xml"
    & $makepri createconfig /cf $priConfig /dq en-US /o | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "makepri createconfig failed ($LASTEXITCODE)" }

    # Drop the <packaging> section so makepri emits one resources.pri instead
    # of splitting per-scale resource packages we don't ship.
    [xml]$cfg = Get-Content $priConfig
    $packagingNode = $cfg.SelectSingleNode("//packaging")
    if ($packagingNode) {
        $packagingNode.ParentNode.RemoveChild($packagingNode) | Out-Null
        $cfg.Save($priConfig)
    }

    & $makepri new /pr $stage /cf $priConfig /of (Join-Path $stage "resources.pri") /o
    if ($LASTEXITCODE -ne 0) { throw "makepri new failed ($LASTEXITCODE)" }
    Write-Host "Built resources.pri"
} else {
    Write-Warning "makepri.exe not found — packaging without resources.pri. Tiles may render blank and Store certification will flag it."
}

# ---------------------------------------------------------------------------
# Pack.
# ---------------------------------------------------------------------------
$msixName = "AnythingToMarkdown-$Version-x64.msix"
$msixPath = Join-Path $OutDir $msixName
if (Test-Path $msixPath) { Remove-Item $msixPath -Force }

& $makeappx pack /d $stage /p $msixPath /o
if ($LASTEXITCODE -ne 0) { throw "makeappx pack failed ($LASTEXITCODE)" }
Write-Host "Packed $msixPath"

# ---------------------------------------------------------------------------
# Signing (optional).
# ---------------------------------------------------------------------------
$pfx = $CertificatePath
$pfxPassword = $CertificatePassword

if ($SelfSign -and -not $pfx) {
    Write-Host "Creating a throwaway self-signed certificate for $Publisher"
    $cert = New-SelfSignedCertificate `
        -Type Custom `
        -Subject $Publisher `
        -KeyUsage DigitalSignature `
        -FriendlyName "AnythingToMarkdown MSIX test certificate" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")

    $pfxPassword = "anytomd-test"
    $pfx = Join-Path $OutDir "AnythingToMarkdown-test.pfx"
    $cerPath = Join-Path $OutDir "AnythingToMarkdown-test.cer"
    $secure = ConvertTo-SecureString -String $pfxPassword -Force -AsPlainText
    Export-PfxCertificate -Cert $cert -FilePath $pfx -Password $secure | Out-Null
    Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null
    Write-Host "Public certificate for trusting on the test machine: $cerPath"
}

if ($pfx) {
    if (-not $signtool) { throw "signtool.exe not found but signing was requested." }
    $signArgs = @("sign", "/fd", "SHA256", "/f", $pfx)
    if ($pfxPassword) { $signArgs += @("/p", $pfxPassword) }
    $signArgs += $msixPath
    & $signtool @signArgs
    if ($LASTEXITCODE -ne 0) { throw "signtool failed ($LASTEXITCODE)" }
    Write-Host "Signed $msixPath"
} else {
    Write-Host "Left unsigned — correct for a Microsoft Store upload (Partner Center signs it)."
}

Remove-Item $stage -Recurse -Force
$sizeMb = [math]::Round((Get-Item $msixPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Built: $msixPath ($sizeMb MB)"
