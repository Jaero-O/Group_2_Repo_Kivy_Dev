import sys
from rembg.bg import remove
from rembg.session_factory import new_session
from PIL import Image

if len(sys.argv) < 3:
    print("Usage: python rembg_runner.py <input> <output>")
    sys.exit(1)

input_img = sys.argv[1]
output_img = sys.argv[2]

session = new_session(model_name="u2net")
img = Image.open(input_img)
result = remove(img, session=session)
result.save(output_img)

print("ok")
