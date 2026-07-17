[CmdletBinding()]
param(
    [string]$ArtifactBaseURL = "https://al-artifacts.tos-ap-southeast-1.volces.com",
    [string]$PublicKey = "FYJ6pbAiSmmE6UnVv4LtKhQaJ3cxJgxyQrZZSAHsosc=",
    [string]$InstallPath = "",
    [switch]$VerifyOnly,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0
Add-Type -AssemblyName System.Numerics
Add-Type -AssemblyName System.Net.Http

$script:Q = [System.Numerics.BigInteger]::Pow([System.Numerics.BigInteger]2, 255) - 19
$script:L = [System.Numerics.BigInteger]::Pow([System.Numerics.BigInteger]2, 252) + [System.Numerics.BigInteger]::Parse("27742317777372353535851937790883648493")

function Get-Mod {
    param(
        [System.Numerics.BigInteger]$Value,
        [System.Numerics.BigInteger]$Modulus
    )
    $Result = $Value % $Modulus
    if ($Result.Sign -lt 0) {
        $Result += $Modulus
    }
    return $Result
}

function Get-FieldInverse {
    param([System.Numerics.BigInteger]$Value)
    return [System.Numerics.BigInteger]::ModPow((Get-Mod $Value $script:Q), $script:Q - 2, $script:Q)
}

$script:D = Get-Mod ((-[System.Numerics.BigInteger]121665) * (Get-FieldInverse 121666)) $script:Q
$script:I = [System.Numerics.BigInteger]::ModPow(2, (($script:Q - 1) / 4), $script:Q)

function Get-XFromY {
    param([System.Numerics.BigInteger]$Y)

    $Y2 = Get-Mod ($Y * $Y) $script:Q
    $XX = Get-Mod (($Y2 - 1) * (Get-FieldInverse (($script:D * $Y2) + 1))) $script:Q
    $X = [System.Numerics.BigInteger]::ModPow($XX, (($script:Q + 3) / 8), $script:Q)
    if ((Get-Mod (($X * $X) - $XX) $script:Q) -ne 0) {
        $X = Get-Mod ($X * $script:I) $script:Q
    }
    if ((Get-Mod (($X * $X) - $XX) $script:Q) -ne 0) {
        throw "invalid Ed25519 point"
    }
    if ((Get-Mod $X 2) -ne 0) {
        $X = $script:Q - $X
    }
    return $X
}

function New-EdPoint {
    param(
        [System.Numerics.BigInteger]$X,
        [System.Numerics.BigInteger]$Y
    )
    return [pscustomobject]@{ X = $X; Y = $Y }
}

function Add-EdPoint {
    param($Left, $Right)

    $X1X2Y1Y2 = Get-Mod ($Left.X * $Right.X * $Left.Y * $Right.Y) $script:Q
    $X = Get-Mod ((($Left.X * $Right.Y) + ($Right.X * $Left.Y)) * (Get-FieldInverse (1 + ($script:D * $X1X2Y1Y2)))) $script:Q
    $Y = Get-Mod ((($Left.Y * $Right.Y) + ($Left.X * $Right.X)) * (Get-FieldInverse (1 - ($script:D * $X1X2Y1Y2)))) $script:Q
    return New-EdPoint $X $Y
}

function Multiply-EdPoint {
    param(
        $Point,
        [System.Numerics.BigInteger]$Scalar
    )

    $Result = New-EdPoint 0 1
    $Current = $Point
    $N = $Scalar
    while ($N -gt 0) {
        if (($N % 2) -eq 1) {
            $Result = Add-EdPoint $Result $Current
        }
        $Current = Add-EdPoint $Current $Current
        $N = $N / 2
    }
    return $Result
}

function ConvertFrom-LittleEndianUnsigned {
    param([byte[]]$Bytes)

    $Unsigned = New-Object byte[] ($Bytes.Length + 1)
    [Array]::Copy($Bytes, 0, $Unsigned, 0, $Bytes.Length)
    return New-Object System.Numerics.BigInteger -ArgumentList @(,$Unsigned)
}

function ConvertTo-EdPoint {
    param([byte[]]$Encoded)

    if ($Encoded.Length -ne 32) {
        throw "invalid Ed25519 point length"
    }
    $Copy = New-Object byte[] 32
    [Array]::Copy($Encoded, $Copy, 32)
    $Sign = ($Copy[31] -shr 7) -band 1
    $Copy[31] = $Copy[31] -band 0x7f
    $Y = ConvertFrom-LittleEndianUnsigned $Copy
    if ($Y -ge $script:Q) {
        throw "non-canonical Ed25519 point"
    }
    $X = Get-XFromY $Y
    if (($X % 2) -ne $Sign) {
        $X = $script:Q - $X
    }

    $Left = Get-Mod (($Y * $Y) - ($X * $X)) $script:Q
    $Right = Get-Mod (1 + ($script:D * $X * $X * $Y * $Y)) $script:Q
    if ($Left -ne $Right) {
        throw "point is not on Ed25519 curve"
    }
    return New-EdPoint $X $Y
}

function Test-Ed25519Signature {
    param(
        [byte[]]$Message,
        [byte[]]$Signature,
        [byte[]]$PublicKeyBytes
    )

    try {
        if (($Signature.Length -ne 64) -or ($PublicKeyBytes.Length -ne 32)) {
            return $false
        }
        [byte[]]$REncoded = $Signature[0..31]
        [byte[]]$SEncoded = $Signature[32..63]
        $S = ConvertFrom-LittleEndianUnsigned $SEncoded
        if ($S -ge $script:L) {
            return $false
        }

        $A = ConvertTo-EdPoint $PublicKeyBytes
        $R = ConvertTo-EdPoint $REncoded
        $BaseY = Get-Mod (4 * (Get-FieldInverse 5)) $script:Q
        $Base = New-EdPoint (Get-XFromY $BaseY) $BaseY

        $HashInput = New-Object byte[] (32 + 32 + $Message.Length)
        [Array]::Copy($REncoded, 0, $HashInput, 0, 32)
        [Array]::Copy($PublicKeyBytes, 0, $HashInput, 32, 32)
        [Array]::Copy($Message, 0, $HashInput, 64, $Message.Length)
        $SHA512 = [System.Security.Cryptography.SHA512]::Create()
        try {
            $Digest = $SHA512.ComputeHash($HashInput)
        }
        finally {
            $SHA512.Dispose()
        }
        $H = (ConvertFrom-LittleEndianUnsigned $Digest) % $script:L

        $Left = Multiply-EdPoint $Base $S
        $Right = Add-EdPoint $R (Multiply-EdPoint $A $H)
        return (($Left.X -eq $Right.X) -and ($Left.Y -eq $Right.Y))
    }
    catch {
        return $false
    }
}

function ConvertFrom-Hex {
    param([string]$Hex)
    if (($Hex.Length % 2) -ne 0) {
        throw "invalid hex length"
    }
    $Result = New-Object byte[] ($Hex.Length / 2)
    for ($Index = 0; $Index -lt $Result.Length; $Index++) {
        $Result[$Index] = [Convert]::ToByte($Hex.Substring($Index * 2, 2), 16)
    }
    return $Result
}

function Invoke-SignatureSelfTest {
    $Key = ConvertFrom-Hex "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    $Signature = ConvertFrom-Hex "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    [byte[]]$Empty = @()
    if (-not (Test-Ed25519Signature $Empty $Signature $Key)) {
        throw "RFC 8032 Ed25519 verification vector failed"
    }
    $Signature[0] = $Signature[0] -bxor 1
    if (Test-Ed25519Signature $Empty $Signature $Key) {
        throw "tampered Ed25519 signature was accepted"
    }
    Write-Host "✓ PowerShell Ed25519 self-test passed"
}

function Get-SHA256Hex {
    param([byte[]]$Bytes)
    $SHA256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Digest = $SHA256.ComputeHash($Bytes)
    }
    finally {
        $SHA256.Dispose()
    }
    return ([BitConverter]::ToString($Digest).Replace("-", "").ToLowerInvariant())
}

function Assert-SafeObjectKey {
    param(
        [string]$Key,
        [string]$Prefix = "credential-agent/"
    )
    if ([string]::IsNullOrWhiteSpace($Key) -or (-not $Key.StartsWith($Prefix))) {
        throw "artifact key is outside the allowed prefix: $Key"
    }
    if (($Key -match "(^|/)\.\.(/|$)") -or $Key.Contains("\\") -or $Key.Contains("//") -or $Key.StartsWith("/")) {
        throw "artifact key is unsafe: $Key"
    }
    if ($Key -notmatch "^[A-Za-z0-9._/-]+$") {
        throw "artifact key contains unsupported characters: $Key"
    }
}

function Get-ArtifactURL {
    param(
        [string]$BaseURL,
        [string]$Key
    )
    Assert-SafeObjectKey $Key
    $Segments = $Key.Split("/") | ForEach-Object { [Uri]::EscapeDataString($_) }
    return $BaseURL.TrimEnd("/") + "/" + ($Segments -join "/")
}

function New-ArtifactHttpClient {
    $Handler = New-Object System.Net.Http.HttpClientHandler
    $Handler.AllowAutoRedirect = $false
    $ProxyURL = $env:HTTPS_PROXY
    if ([string]::IsNullOrWhiteSpace($ProxyURL)) {
        $ProxyURL = $env:HTTP_PROXY
    }
    if (-not [string]::IsNullOrWhiteSpace($ProxyURL)) {
        $ProxyURI = $null
        if ([Uri]::TryCreate($ProxyURL, [UriKind]::Absolute, [ref]$ProxyURI)) {
            $Handler.Proxy = New-Object System.Net.WebProxy($ProxyURI)
            $Handler.UseProxy = $true
        }
    }
    $Client = New-Object System.Net.Http.HttpClient($Handler)
    $Client.Timeout = [TimeSpan]::FromMinutes(30)
    return $Client
}

function Get-HTTPSBytes {
    param(
        [System.Net.Http.HttpClient]$Client,
        [string]$URL,
        [long]$MaxBytes
    )
    $URI = New-Object Uri($URL)
    if ($URI.Scheme -ne "https") {
        throw "refusing non-HTTPS artifact URL: $URL"
    }
    $Response = $Client.GetAsync($URI, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
    try {
        if (-not $Response.IsSuccessStatusCode) {
            throw "artifact request failed with HTTP $([int]$Response.StatusCode): $URL"
        }
        $Length = $Response.Content.Headers.ContentLength
        if (($null -ne $Length) -and ($Length -gt $MaxBytes)) {
            throw "artifact response exceeds size limit: $URL"
        }
        $Bytes = $Response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
        if ($Bytes.Length -gt $MaxBytes) {
            throw "artifact response exceeds size limit: $URL"
        }
        return $Bytes
    }
    finally {
        $Response.Dispose()
    }
}

function Save-HTTPSFile {
    param(
        [System.Net.Http.HttpClient]$Client,
        [string]$URL,
        [string]$Destination,
        [long]$ExpectedSize
    )
    $URI = New-Object Uri($URL)
    if ($URI.Scheme -ne "https") {
        throw "refusing non-HTTPS artifact URL: $URL"
    }

    $LastError = $null
    for ($Attempt = 1; $Attempt -le 3; $Attempt++) {
        try {
            $Response = $Client.GetAsync($URI, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
            try {
                if (-not $Response.IsSuccessStatusCode) {
                    throw "artifact request failed with HTTP $([int]$Response.StatusCode)"
                }
                $Stream = $Response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
                try {
                    $File = New-Object System.IO.FileStream($Destination, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
                    try {
                        $Buffer = New-Object byte[] 262144
                        [long]$Written = 0
                        [int]$LastPercent = -1
                        while (($Read = $Stream.Read($Buffer, 0, $Buffer.Length)) -gt 0) {
                            $File.Write($Buffer, 0, $Read)
                            $Written += $Read
                            if ($ExpectedSize -gt 0) {
                                $Percent = [Math]::Min(100, [int](($Written * 100) / $ExpectedSize))
                                if (($Percent -ge ($LastPercent + 5)) -or ($Percent -eq 100)) {
                                    Write-Progress -Activity "Downloading Credential Agent" -Status "$Percent%  $([Math]::Round($Written / 1MB, 1))/$([Math]::Round($ExpectedSize / 1MB, 1)) MiB" -PercentComplete $Percent
                                    $LastPercent = $Percent
                                }
                            }
                        }
                    }
                    finally {
                        $File.Dispose()
                    }
                }
                finally {
                    $Stream.Dispose()
                }
            }
            finally {
                $Response.Dispose()
            }
            Write-Progress -Activity "Downloading Credential Agent" -Completed
            return
        }
        catch {
            $LastError = $_
            Write-Progress -Activity "Downloading Credential Agent" -Completed
            Remove-Item $Destination -Force -ErrorAction SilentlyContinue
            if ($Attempt -lt 3) {
                Write-Warning "Agent download attempt $Attempt failed; retrying"
                Start-Sleep -Seconds ([Math]::Pow(2, $Attempt))
            }
        }
    }
    throw $LastError
}

function Get-WindowsPlatform {
    $Architecture = $env:PROCESSOR_ARCHITEW6432
    if ([string]::IsNullOrWhiteSpace($Architecture)) {
        $Architecture = $env:PROCESSOR_ARCHITECTURE
    }
    if ([string]::IsNullOrWhiteSpace($Architecture)) {
        return "windows/amd64"
    }
    switch ($Architecture.ToUpperInvariant()) {
        "AMD64" { return "windows/amd64" }
        "ARM64" { return "windows/arm64" }
        default { throw "unsupported Windows architecture: $Architecture" }
    }
}

if ($SelfTest) {
    Invoke-SignatureSelfTest
    exit 0
}

$BaseURI = $null
if (-not [Uri]::TryCreate($ArtifactBaseURL, [UriKind]::Absolute, [ref]$BaseURI)) {
    throw "invalid artifact base URL"
}
if (($BaseURI.Scheme -ne "https") -or (-not [string]::IsNullOrEmpty($BaseURI.UserInfo)) -or (-not [string]::IsNullOrEmpty($BaseURI.Query)) -or (-not [string]::IsNullOrEmpty($BaseURI.Fragment))) {
    throw "artifact base URL must be an HTTPS origin or path without credentials, query, or fragment"
}
$ArtifactBaseURL = $ArtifactBaseURL.TrimEnd("/")

try {
    $PublicKeyBytes = [Convert]::FromBase64String($PublicKey)
}
catch {
    throw "release public key is not valid base64"
}
if ($PublicKeyBytes.Length -ne 32) {
    throw "release public key must be 32 bytes"
}

$Client = New-ArtifactHttpClient
try {
    Write-Host "Checking signed Credential Agent release..."
    $LatestURL = Get-ArtifactURL $ArtifactBaseURL "credential-agent/latest.json"
    $LatestBytes = Get-HTTPSBytes $Client $LatestURL 1048576
    $Latest = [Text.Encoding]::UTF8.GetString($LatestBytes) | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$Latest.version)) {
        throw "latest metadata does not contain a version"
    }
    Assert-SafeObjectKey ([string]$Latest.manifestKey)
    Assert-SafeObjectKey ([string]$Latest.manifestSignatureKey)

    $ManifestURL = Get-ArtifactURL $ArtifactBaseURL ([string]$Latest.manifestKey)
    $SignatureURL = Get-ArtifactURL $ArtifactBaseURL ([string]$Latest.manifestSignatureKey)
    $ManifestBytes = Get-HTTPSBytes $Client $ManifestURL 4194304
    $ActualManifestSHA256 = Get-SHA256Hex $ManifestBytes
    if ($ActualManifestSHA256 -ne ([string]$Latest.manifestSHA256).ToLowerInvariant()) {
        throw "release manifest SHA256 mismatch"
    }
    $SignatureText = [Text.Encoding]::ASCII.GetString((Get-HTTPSBytes $Client $SignatureURL 16384)).Trim()
    try {
        $SignatureBytes = [Convert]::FromBase64String($SignatureText)
    }
    catch {
        throw "release manifest signature is not valid base64"
    }
    if (-not (Test-Ed25519Signature $ManifestBytes $SignatureBytes $PublicKeyBytes)) {
        throw "release manifest Ed25519 signature verification failed"
    }

    $Manifest = [Text.Encoding]::UTF8.GetString($ManifestBytes) | ConvertFrom-Json
    if ([string]$Manifest.version -ne [string]$Latest.version) {
        throw "release version differs between latest metadata and manifest"
    }
    $Platform = Get-WindowsPlatform
    $Artifact = @($Manifest.files | Where-Object {
        ($_.PSObject.Properties.Name -contains "platform") -and ([string]$_.platform -eq $Platform)
    })
    if ($Artifact.Count -ne 1) {
        throw "signed release does not contain exactly one artifact for $Platform"
    }
    $Artifact = $Artifact[0]
    Assert-SafeObjectKey ([string]$Artifact.key)
    if (([long]$Artifact.size -le 0) -or ([string]$Artifact.sha256 -notmatch "^[a-fA-F0-9]{64}$")) {
        throw "signed release artifact metadata is invalid"
    }

    Write-Host "✓ Signed release verified: $($Manifest.version) ($Platform, $([Math]::Round(([long]$Artifact.size) / 1MB, 1)) MiB)"
    if ($VerifyOnly) {
        [ordered]@{
            version = [string]$Manifest.version
            platform = $Platform
            key = [string]$Artifact.key
            size = [long]$Artifact.size
            sha256 = ([string]$Artifact.sha256).ToLowerInvariant()
            manifestSHA256 = $ActualManifestSHA256
        } | ConvertTo-Json -Compress
        exit 0
    }

    if ($env:OS -ne "Windows_NT") {
        throw "installation is only supported on Windows; use -VerifyOnly for cross-platform validation"
    }
    if ([string]::IsNullOrWhiteSpace($InstallPath)) {
        if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
            throw "LOCALAPPDATA is unavailable"
        }
        $InstallPath = Join-Path $env:LOCALAPPDATA "AL\CredentialAgent\credential-agent.exe"
    }
    $InstallPath = [IO.Path]::GetFullPath($InstallPath)
    $InstallDirectory = Split-Path -Parent $InstallPath
    New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null

    if (Test-Path -LiteralPath $InstallPath -PathType Leaf) {
        Write-Host "Delegating replacement to the installed Agent updater..."
        & $InstallPath update --manifest $ManifestURL --signature $SignatureURL --public-key $PublicKey --artifact-base-url $ArtifactBaseURL
        if ($LASTEXITCODE -ne 0) {
            throw "installed Agent updater failed with exit code $LASTEXITCODE; the existing executable was left unchanged"
        }
        Write-Host "✓ Credential Agent update was accepted"
        exit 0
    }

    $ArtifactURL = Get-ArtifactURL $ArtifactBaseURL ([string]$Artifact.key)
    $StagedPath = $InstallPath + ".new.exe"
    Remove-Item $StagedPath -Force -ErrorAction SilentlyContinue
    Save-HTTPSFile $Client $ArtifactURL $StagedPath ([long]$Artifact.size)
    $StagedInfo = Get-Item -LiteralPath $StagedPath
    if ($StagedInfo.Length -ne [long]$Artifact.size) {
        Remove-Item $StagedPath -Force -ErrorAction SilentlyContinue
        throw "downloaded Agent length does not match signed manifest"
    }
    $ActualArtifactSHA256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $StagedPath).Hash.ToLowerInvariant()
    if ($ActualArtifactSHA256 -ne ([string]$Artifact.sha256).ToLowerInvariant()) {
        Remove-Item $StagedPath -Force -ErrorAction SilentlyContinue
        throw "downloaded Agent SHA256 does not match signed manifest"
    }
    Move-Item -LiteralPath $StagedPath -Destination $InstallPath
    & $InstallPath help | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "installed Agent smoke test failed"
    }
    Write-Host "✓ Credential Agent installed: $InstallPath"
}
finally {
    if ($null -ne $Client) {
        $Client.Dispose()
    }
}
