[CmdletBinding()]
param()

$Agent = if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $null
} else {
    Join-Path $env:LOCALAPPDATA "AL\CredentialAgent\credential-agent.exe"
}

$ChromeCandidates = @()
foreach ($Base in @($env:PROGRAMFILES, ${env:PROGRAMFILES(X86)}, $env:LOCALAPPDATA)) {
    if (-not [string]::IsNullOrWhiteSpace($Base)) {
        $ChromeCandidates += Join-Path $Base "Google\Chrome\Application\chrome.exe"
    }
}
$Chrome = $ChromeCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
$Arch = switch ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()) {
    "X64" { "amd64" }
    "Arm64" { "arm64" }
    default { $_.ToLowerInvariant() }
}

[ordered]@{
    schema_version = 1
    os = "windows"
    arch = $Arch
    interactive = [Environment]::UserInteractive
    chrome = [ordered]@{
        installed = -not [string]::IsNullOrWhiteSpace($Chrome)
        executable = $Chrome
    }
    agent = [ordered]@{
        installed = $null -ne $Agent -and (Test-Path -LiteralPath $Agent -PathType Leaf)
        path = $Agent
    }
} | ConvertTo-Json -Depth 4 -Compress
