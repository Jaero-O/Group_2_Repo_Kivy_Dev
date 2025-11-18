"""
Verify local ML model files are present and download missing ones from the repository's GitHub Release.

Usage:
    python scripts/verify_models_present.py --tag v1.0-models --repo Jaero-O/Group_2_Repo_Kivy_Dev --dest ml/Plant_Disease_Prediction

The script checks for models under `<dest>/h5/` and `<dest>/tflite/`. If any files are missing, it calls
`scripts/download_models.py` to fetch release assets for the provided tag into the destination directory.

If your release is private or you need higher request limits, set the environment variable `GITHUB_TOKEN`.
"""
import argparse
import os
import subprocess
import sys

H5_REQUIRED = [
    # filenames expected in h5/ (may be optional depending on your workflow)
    'fine_tuned_model.h5',
    'ft1_mango_leaf_disease.h5',
    'mango_leaf_disease_mobilenetv2.h5'
]

TFLITE_REQUIRED = [
    'ft1_mango_mobilenetv2.tflite',
    'mango_mobilenetv2.tflite',
    'v1_mango_mobilenetv2.tflite'
]


def exists_in_dir(dirname, filenames):
    if not os.path.isdir(dirname):
        return []
    present = []
    for f in filenames:
        if os.path.exists(os.path.join(dirname, f)):
            present.append(f)
    return present


def run_downloader(tag, repo, dest):
    cmd = [sys.executable, os.path.join('scripts', 'download_models.py'), '--repo', repo, '--tag', tag, '--dest', dest]
    print('Running downloader:', ' '.join(cmd))
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print('Downloader failed:', e)
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tag', default='v1.0-models', help='Release tag to fetch from')
    p.add_argument('--repo', default='Jaero-O/Group_2_Repo_Kivy_Dev', help='owner/repo')
    p.add_argument('--dest', default=os.path.join('ml', 'Plant_Disease_Prediction'), help='destination directory')
    args = p.parse_args()

    dest = args.dest
    h5_dir = os.path.join(dest, 'h5')
    tflite_dir = os.path.join(dest, 'tflite')

    print('Checking for H5 models in', h5_dir)
    present_h5 = exists_in_dir(h5_dir, H5_REQUIRED)
    missing_h5 = [f for f in H5_REQUIRED if f not in present_h5]

    print('Checking for TFLite models in', tflite_dir)
    present_tflite = exists_in_dir(tflite_dir, TFLITE_REQUIRED)
    missing_tflite = [f for f in TFLITE_REQUIRED if f not in present_tflite]

    if not missing_h5 and not missing_tflite:
        print('All required model files appear present locally.')
        return 0

    print('Missing H5:', missing_h5)
    print('Missing TFLite:', missing_tflite)

    # Attempt to download via existing helper
    print('Attempting to download release assets into', dest)
    ok = run_downloader(args.tag, args.repo, dest)
    if not ok:
        print('Download failed. Please ensure network access and that the release exists.')
        return 2

    # Re-check
    present_h5 = exists_in_dir(h5_dir, H5_REQUIRED)
    present_tflite = exists_in_dir(tflite_dir, TFLITE_REQUIRED)
    missing_h5 = [f for f in H5_REQUIRED if f not in present_h5]
    missing_tflite = [f for f in TFLITE_REQUIRED if f not in present_tflite]

    if not missing_h5 and not missing_tflite:
        print('Download complete: all required files present.')
        return 0
    else:
        print('After download, still missing:')
        print('H5:', missing_h5)
        print('TFLite:', missing_tflite)
        return 3


if __name__ == '__main__':
    sys.exit(main())
