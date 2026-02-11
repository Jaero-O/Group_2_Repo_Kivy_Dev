import argparse
import os
import shutil
from pathlib import Path

ML_TARGET_ROOT = Path('ml')
TRAINING_DIR = ML_TARGET_ROOT / 'training'
TFLITE_DIR = ML_TARGET_ROOT / 'Plant_Disease_Prediction' / 'tflite'
ASSETS_DIR = ML_TARGET_ROOT / 'assets'

LABEL_CANDIDATES = ['labels.txt', 'label_map.txt', 'classes.txt']
NOTEBOOK_EXT = '.ipynb'
MODEL_EXTS = ['.tflite']

EXCLUDE_DIR_NAMES = {'__pycache__', '.git', 'dataset', 'data', 'captures', 'processed'}


def copy_if_exists(src: Path, dest: Path):
    if src.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f'Copied {src} -> {dest}')
        return True
    return False


def discover_files(root: Path):
    notebooks = []
    models = []
    labels = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        for f in filenames:
            p = Path(dirpath) / f
            if p.suffix == NOTEBOOK_EXT:
                notebooks.append(p)
            if p.name in LABEL_CANDIDATES:
                labels.append(p)
            if p.suffix in MODEL_EXTS:
                models.append(p)
    return notebooks, models, labels


def sync(source: Path, copy_notebooks: bool, overwrite: bool):
    if not source.exists():
        raise FileNotFoundError(f'Source path not found: {source}')
    print(f'Scanning source: {source}')
    notebooks, models, labels = discover_files(source)
    print(f'Found notebooks: {len(notebooks)}, models: {len(models)}, label files: {len(labels)}')

    # Copy first model (or all if multiple?)
    for m in models[:1]:
        dest = TFLITE_DIR / m.name
        if dest.exists() and not overwrite:
            print(f'Skipping existing model (use --overwrite to replace): {dest}')
        else:
            copy_if_exists(m, dest)

    # Copy first label file
    for l in labels[:1]:
        dest = ASSETS_DIR / 'labels.txt'
        if dest.exists() and not overwrite:
            print(f'Skipping existing labels (use --overwrite to replace): {dest}')
        else:
            copy_if_exists(l, dest)
        break

    # Copy notebooks
    if copy_notebooks:
        for nb in notebooks:
            dest = TRAINING_DIR / nb.name
            if dest.exists() and not overwrite:
                print(f'Skipping existing notebook: {dest}')
            else:
                copy_if_exists(nb, dest)

    print('Sync complete.')
    print('Environment overrides:')
    print('  MANGOFY_MODEL_PATH=', (TFLITE_DIR / models[0].name).resolve() if models else 'N/A')
    print('  MANGOFY_LABELS_PATH=', (ASSETS_DIR / 'labels.txt').resolve())


def main():
    parser = argparse.ArgumentParser(description='Sync external ML assets into local repo.')
    parser.add_argument('--source', required=True, help='Path to external Group_2_Repo root')
    parser.add_argument('--no-notebooks', action='store_true', help='Skip copying training notebooks')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing local assets')
    args = parser.parse_args()

    source = Path(args.source).expanduser()
    sync(source, copy_notebooks=not args.no_notebooks, overwrite=args.overwrite)


if __name__ == '__main__':
    main()
