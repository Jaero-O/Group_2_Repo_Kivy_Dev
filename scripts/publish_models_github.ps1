<#
PowerShell script to create a GitHub Release and upload model assets using the `gh` CLI.

Prerequisites:
- `gh` (GitHub CLI) installed and authenticated (run `gh auth login` first).
- Run this from the repo root.

Usage:
  .\scripts\publish_models_github.ps1 -Tag v1.0-models -Title "ML models v1" -Notes "Models extracted from repo"

#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Tag,
    [string]$Title = "ML models",
    [string]$Notes = "Model files and tflite assets",
    [string]$Pattern = "ml/Plant_Disease_Prediction/h5/*,ml/Plant_Disease_Prediction/tflite/*"
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI 'gh' not found. Install it and run 'gh auth login' before using this script."
    exit 1
}

$files = @()
foreach ($p in $Pattern -split ',') {
    $matches = Get-ChildItem -Path $p -File -ErrorAction SilentlyContinue
    foreach ($m in $matches) { $files += $m.FullName }
}

if ($files.Count -eq 0) {
    Write-Host "No files found for patterns: $Pattern"
    exit 0
}

Write-Host "Creating release $Tag and uploading $($files.Count) assets..."

gh release create $Tag @files --title "$Title" --notes "$Notes"

if ($LASTEXITCODE -ne 0) {
    Write-Error "gh release create failed. You can try uploading assets manually with 'gh release upload'."
    exit $LASTEXITCODE
}

Write-Host "Release created and assets uploaded."
