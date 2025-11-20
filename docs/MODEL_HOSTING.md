**Model Hosting & Collaborator Sync**
- **Purpose**: store large ML model files outside Git history and provide helpers to upload and download them.

**Recommended non-paid hosting**
- GitHub Releases (good for storing release assets; no extra cost for small numbers of files). We provide scripts to publish and download assets.
- Google Drive (free quota) — requires manual upload and shareable link; downloader can be adapted to use file ids.

**Uploading models to GitHub Releases (recommended)**
- Prereqs: `gh` (GitHub CLI) installed and authenticated.
- From repo root (PowerShell):

```
# Example: create a release and upload assets found by patterns
.
\scripts\publish_models_github.ps1 -Tag v1.0-models -Title "ML models v1" -Notes "Models extracted from repo"
```

- The script will look for `ml/Plant_Disease_Prediction/h5/*` and `ml/Plant_Disease_Prediction/tflite/*` by default. Adjust the `-Pattern` argument to include other paths.

**Downloading models (for CI / dev machines)**
- Simple Python helper is included at `scripts/download_models.py`.
- Usage:

```
python scripts/download_models.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest models/
```

- For private repos or higher rate limits, export your token first:

```
$env:GITHUB_TOKEN = "<your_token>"
python scripts/download_models.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest models/
```

**Alternative: Google Drive**
- Upload the model files to a shared Drive folder and provide a link in the README.
- The `scripts/download_models.py` can be extended to download from Google Drive given a file id.

**Collaborator sync after history rewrite**
Because the `integration` branch history was rewritten to remove large files from history, collaborators with existing clones must update their local clones.

Recommended (safe) approach — re-clone the repo:

```
# Re-clone fresh
git clone https://github.com/Jaero-O/Group_2_Repo_Kivy_Dev.git
cd Group_2_Repo_Kivy_Dev
git checkout integration
```

Advanced alternative — retain local changes (careful):
1. Fetch the updated branches and reset your local branch to match remote:

```
git fetch origin
git checkout integration
git reset --hard origin/integration
```

2. If you have local commits to preserve, create a patch or branch them off, then reapply (rebase or cherry-pick) onto the new history.

**Notes & Warnings**
- Rewriting history is destructive; re-cloning is the simplest approach for collaborators.
- The scripts provided depend on `gh` or `requests` (Python). Install dependencies as needed.

**Next steps for maintainers**
- Consider creating a documented release with a stable tag (e.g., `v1.0-models`) containing all models.
- Add a short CI job step to `scripts/download_models.py` in workflows to fetch models for tests.
- If you prefer storing models in cloud storage (Google Drive / S3), I can add upload scripts for those services.
