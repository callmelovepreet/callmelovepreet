"""Prep a photo for ASCII conversion.

Removes the background, boosts local contrast with CLAHE and composites the
subject onto pure white. Writes source-prepped.png (grayscale plus the
subject mask as alpha) to the repo root; the alpha lets make_ascii_svg.py
blank out the background exactly.

    python scripts/prep_photo.py source-photo.jpg
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "source-prepped.png"


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "source-photo.jpg"
    photo = Image.open(src).convert("RGB")

    # 1. Isolate the subject.
    cut = remove(photo).convert("RGBA")
    rgba = np.array(cut)
    alpha = rgba[:, :, 3].astype(np.float32) / 255.0

    # 2. Boost local contrast so a flatly lit subject gets real highlights.
    gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray).astype(np.float32)

    # 3. Composite onto white so the background becomes spaces.
    out = gray * alpha + 255.0 * (1.0 - alpha)

    # Crop to the subject's bounding box with a small margin.
    ys, xs = np.where(alpha > 0.1)
    if len(xs):
        pad = 8
        y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, out.shape[0])
        x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, out.shape[1])
        out = out[y0:y1, x0:x1]

        alpha = alpha[y0:y1, x0:x1]

    gray_img = Image.fromarray(out.clip(0, 255).astype(np.uint8), "L")
    mask_img = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    Image.merge("LA", (gray_img, mask_img)).save(OUT)
    print(f"wrote {OUT.name} ({out.shape[1]}x{out.shape[0]})")


if __name__ == "__main__":
    main()
