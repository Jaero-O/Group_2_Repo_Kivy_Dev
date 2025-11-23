<#
  PowerShell helper script to stage, commit, and push repository contents
  Implements separate commits: config (gitignore/gitattributes), DB, code, docs, artifacts
  Designed for branch 'stabilize/baseline-2025-11-20' by default; change TARGET_BRANCH to use a different branch
#>

param(
    [string] $TargetBranch = 'stabilize/baseline-2025-11-20',
    [switch] $Push = $false,
    [switch] $IncludeDb = $true,
    [switch] $IncludeVenv = $false,
    [switch] $UseLFS = $true
)

function Confirm-Run([string]$message) {
    $resp = Read-Host "$message (y/N)"
    return $resp -match '^[Yy]'
}

Write-Host "Branch check and status..." -ForegroundColor Cyan
$current = git rev-parse --abbrev-ref HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not a git repository or git not available. Aborting."
    exit 1
}
Write-Host "Current branch: $current"
if ($current -ne $TargetBranch) {
    Write-Host "Switching to target branch $TargetBranch" -ForegroundColor Yellow
    git checkout $TargetBranch
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to checkout $TargetBranch"; exit 1 }
}

# Git LFS setup
if ($UseLFS) {
    if (Get-Command git-lfs -ErrorAction SilentlyContinue) {
        Write-Host "Configuring Git LFS..." -ForegroundColor Cyan
        git lfs install --local
        # Track configured large file patterns from .gitattributes (also safe to run)
        git lfs track "*.tflite" "*.h5" "*.onnx" "*.db" "*.npz" "*.tar.gz" "*.jpg" "*.jpeg" "*.png" "*.csv" 2>$null || $null
        git add .gitattributes
        if (-not (git diff --staged --quiet)) { git commit -m "chore(lfs): track large file types via git-lfs" -q }
    } else {
        Write-Warning "git-lfs not found on PATH; skipping LFS setup. Install git lfs for better large-file handling."
    }
}

# 1) Commit config files: .gitattributes and .gitignore
Write-Host "Staging config files (.gitignore, .gitattributes)..." -ForegroundColor Cyan
git add .gitignore .gitattributes
if (git diff --staged --quiet) { Write-Host "No changes to commit for configs" -ForegroundColor Green } else {
    git commit -m "chore(repo): update .gitignore and .gitattributes for baseline" -q
}

# 2) Commit DB if requested
if ($IncludeDb) {
    if (Test-Path -Path mangofy.db) {
        Write-Host "Staging DB file (mangofy.db)..." -ForegroundColor Cyan
        git add mangofy.db
        if (-not (git diff --staged --quiet)) {
            git commit -m "feat(db): add/updated mangofy.db (development database snapshot)" -q
        } else { Write-Host "No staged changes for DB" -ForegroundColor Green }
    } else { Write-Host "mangofy.db not found in repo root, skipping DB commit" -ForegroundColor Yellow }
}

# 3) Commit source code in logical groups (src, kivy-lcd-app, tools)
Write-Host "Staging source files (src, kivy-lcd-app, tools)..." -ForegroundColor Cyan
git add src kivy-lcd-app tools ml kivi-lcd-app 2>$null
git add -A -- ':!screenshots' ':!artifacts' ':!.venv' ':!.venv/*' 2>$null || $null
if (-not (git diff --staged --quiet)) {
    git commit -m "feat(app): implement source baseline for Kivy app, ml, and tools" -q
} else { Write-Host "No staged source changes" -ForegroundColor Green }

# 4) Commit docs and README
Write-Host "Staging documentation and README..." -ForegroundColor Cyan
git add README.md docs docs/* .github CONTRIBUTING || $null
if (-not (git diff --staged --quiet)) {
    git commit -m "docs: add documentation and guides for baseline" -q
} else { Write-Host "No staged doc changes" -ForegroundColor Green }

# 5) Add other assets / screenshots if present (ask the user)
if (Test-Path -Path screenshots -PathType Container) {
    if (Confirm-Run "Include screenshots and visual artifacts in commit? This may increase repo size.") {
        git add screenshots artifacts exports
        if (-not (git diff --staged --quiet)) { git commit -m "chore: add visual artifacts and screenshots" -q }
    } else { Write-Host "Skipping screenshots/artifacts" }
}

# 6) OPTIONAL: If including .venv (not recommended), commit explicitly (user passed $IncludeVenv)
if ($IncludeVenv) {
    if (Test-Path -Path .venv) {
        Write-Warning "Including .venv in commits is not recommended; commit size will be very large and OS specific; proceeding on user request."
        git add .venv
        git commit -m "chore: include local .venv snapshot (not recommended for long-term)" -q
    }
}

# 7) Push commits
if ($Push) {
    Write-Host "Pushing changes to origin/$TargetBranch" -ForegroundColor Cyan
    git push origin $TargetBranch
    if ($LASTEXITCODE -ne 0) { Write-Error "Push failed"; exit 1 }
    Write-Host "Pushed to origin/$TargetBranch" -ForegroundColor Green
} else {
    Write-Host "Done creating commits locally. Use --Push to push to remote. Exiting without pushing." -ForegroundColor Yellow
}

Write-Host "All done — please review commits and push PR as needed." -ForegroundColor Cyan
