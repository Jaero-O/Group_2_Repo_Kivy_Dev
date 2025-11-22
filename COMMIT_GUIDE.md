# Commit & Push Guide (Baseline)

This guide packages the recommended steps and options to push your repository baseline, including suggestions for handling large files and the `mangofy.db` file.

Overview
- We recommend creating a small number of clear, separate commits: _configuration_, _DB_, _source code_, _docs_, and optionally _visual assets_. This separates concerns and makes reviews easier.
- `.venv` and user-specific virtual environments should by default be excluded; if you need to include it for an offline runnable snapshot, do so explicitly and be aware of the repo size implications.
- `mangofy.db` intentionally lives in the repository root — the project expects it for development/test implementation from the repo snapshot.

Commands (interactive helper)
1) Configure environment (if needed):
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Prepare and run the commit helper script (recommended):
```powershell
# Set to true if you want to include DB and files
.
scripts\commit_and_push_all.ps1 -TargetBranch stabilize/baseline-2025-11-20 -Push:$false -IncludeDb:$true -IncludeVenv:$false -UseLFS:$true
```
- Use `-Push:$true` to directly push all commits to the remote branch (use with caution).
- If the script stops early, it will print helpful messages about the actions and how to complete them manually.

Large file handling (free and seamless options)

1) Git LFS (Recommended): Git LFS is the most seamless option for tracking large files while still keeping references in Git. It stores the actual blobs separately and keeps lightweight pointers in your repo history. Free tier on GitHub exists but has a storage & bandwidth quota; check your account limits.
   - Setup: `git lfs install` + `git lfs track "*.tflite" "*.h5" "*.db" "*.npz"`.
   - Advantages: Seamless to developers who have LFS installed; small repo size for code reviewers.
   - Limitations: Requires `git lfs` and remote LFS support; GitHub free tier has a cap (data packs). The `.gitattributes` file is included to help track common large file types.

2) GitHub Releases / Release Artifacts: Attach large binary files to a release (manual but free). Your code references the release assets for runtime.
   - Advantages: No LFS quota; downloads are separate from the codebase.
   - Limitations: Not automatically versioned by Git commits; you must maintain the release artifacts separately.

3) External Storage (S3, Google Drive, Azure Storage) + Download Script: Keep large models on external storage and add a `scripts/download_model.py` to fetch them during setup.
   - Advantages: No git storage usage and flexible.
   - Limitations: Adds dependency on storage access or tokens (private), and may be a step for CI.

4) Split & Compress: For some assets, splitting or compressing reduces size and may fit in Git; not suitable for models.

Notes & Risk Controls
- Do not accidentally commit user secrets or environment files. If you find a secret in the repo history, remove it and rotate credentials.
- If the repo is already public, be careful with DB content: it may contain sensitive data. Check before committing.

If you want me to run the helper script or make the actual git commits in the workspace, confirm whether you want to push to the remote now. I can prepare the repo files and finalize the commit commands for you to run.
