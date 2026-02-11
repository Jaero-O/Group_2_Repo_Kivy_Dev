# remove_bg.py

import sys
import json
from rembg import remove
from rembg.session_factory import new_session
from PIL import Image

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "args: input.png output.png"}))
        return

    in_path = sys.argv[1]
    out_path = sys.argv[2]

    try:
        session = new_session(model_name="u2net")
        im = Image.open(in_path)
        result = remove(im, session=session)
        result.save(out_path)

        print(json.dumps({"status": "ok"}))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
