[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ExtensionDirectory
)

$ErrorActionPreference = "Stop"
$Directory = (Resolve-Path -LiteralPath $ExtensionDirectory).Path
if (-not (Test-Path -LiteralPath (Join-Path $Directory "manifest.json") -PathType Leaf)) {
    throw "extension directory is missing manifest.json"
}
$Chrome = $null
foreach ($Base in @($env:PROGRAMFILES, ${env:PROGRAMFILES(X86)}, $env:LOCALAPPDATA)) {
    if ([string]::IsNullOrWhiteSpace($Base)) { continue }
    $Candidate = Join-Path $Base "Google\Chrome\Application\chrome.exe"
    if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
        $Chrome = $Candidate
        break
    }
}
if ([string]::IsNullOrWhiteSpace($Chrome)) {
    throw "Google Chrome is not installed"
}
Start-Process explorer.exe -ArgumentList @($Directory)
Start-Process -FilePath $Chrome -ArgumentList @("--new-window", "chrome://extensions/")
[ordered]@{ ok = $true; directory = $Directory; url = "chrome://extensions/" } |
    ConvertTo-Json -Compress
