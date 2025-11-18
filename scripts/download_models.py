"""
Download release assets (models) from GitHub Releases for this repository.

Usage examples:
  python scripts/download_models.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest models/

Notes:
- For private repos or higher rate limits, set environment variable GITHUB_TOKEN with a personal access token.
- This script will fetch the release by tag and download each asset to the destination directory.
"""
import os
import sys
import argparse
import requests

API = "https://api.github.com"


def get_release_by_tag(owner_repo, tag, token=None):
    url = f"{API}/repos/{owner_repo}/releases/tags/{tag}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def download_asset(asset, dest_dir, token=None):
    url = asset["url"]  # this is the API URL for the asset
    headers = {"Accept": "application/octet-stream"}
    if token:
        headers["Authorization"] = f"token {token}"
    r = requests.get(url, headers=headers, stream=True)
    r.raise_for_status()
    filename = os.path.join(dest_dir, asset["name"])
    with open(filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"Downloaded {asset['name']} -> {filename}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="owner/repo, e.g. Jaero-O/Group_2_Repo_Kivy_Dev")
    p.add_argument("--tag", required=True, help="release tag to fetch assets from")
    p.add_argument("--dest", default="models", help="destination directory")
    args = p.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    owner_repo = args.repo
    tag = args.tag
    dest = args.dest
    os.makedirs(dest, exist_ok=True)

    release = get_release_by_tag(owner_repo, tag, token=token)
    assets = release.get("assets", [])
    if not assets:
        print("No assets found on this release.")
        return

    for asset in assets:
        download_asset(asset, dest, token=token)


if __name__ == "__main__":
    main()
