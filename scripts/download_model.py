import argparse
import os
import sys
import urllib.request

GITHUB_RAW_URL = "https://raw.githubusercontent.com/Jaero-O/Group_2_Repo/main/Plant_Disease_Prediction/tflite/mango_mobilenetv2.tflite"
DEFAULT_DEST = os.path.join("ml","Plant_Disease_Prediction","tflite","mango_mobilenetv2.tflite")

LABELS_RAW_URL = "https://raw.githubusercontent.com/Jaero-O/Group_2_Repo/main/Plant_Disease_Prediction/tflite/labels.txt"
LABELS_DEST = os.path.join("ml","assets","labels.txt")


def download(url: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"Downloading {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Download TFLite model and labels for MangoFy")
    parser.add_argument("--model-url", default=GITHUB_RAW_URL, help="Raw URL to TFLite model")
    parser.add_argument("--labels-url", default=LABELS_RAW_URL, help="Raw URL to labels file")
    parser.add_argument("--model-dest", default=DEFAULT_DEST, help="Destination path for model")
    parser.add_argument("--labels-dest", default=LABELS_DEST, help="Destination path for labels")
    args = parser.parse_args()

    try:
        download(args.model_url, args.model_dest)
    except Exception as e:
        print("Model download failed:", e)
        sys.exit(1)

    try:
        download(args.labels_url, args.labels_dest)
    except Exception as e:
        print("Labels download failed:", e)
        sys.exit(1)

    print("All assets downloaded.")
    print("Set environment variables if using external paths:")
    print("  MANGOFY_MODEL_PATH=", os.path.abspath(args.model_dest))
    print("  MANGOFY_LABELS_PATH=", os.path.abspath(args.labels_dest))


if __name__ == "__main__":
    main()
