"""Phase 1 helper - ROUGH ground-truth mask assist.

For each product image this runs OpenCV GrabCut seeded from a centre rectangle and
writes a black/white mask PNG to the ground-truth folder. GrabCut is a classical
segmenter, NOT the model under test, so it is a fair (independent) starting point.

IMPORTANT: these masks are a starting point only. Open each one in any image
editor and hand-correct it (paint product = white, background = black) before you
trust the IoU numbers. The whole point of Phase 1 is a *hand-labelled* reference.
The script prints which masks look least confident so you know where to focus.

Usage:
    python -m eval.make_ground_truth --images eval/test_images --out eval/ground_truth
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def grabcut_mask(bgr: np.ndarray, margin: float = 0.08, iters: int = 8) -> np.ndarray:
    h, w = bgr.shape[:2]
    rect = (int(w * margin), int(h * margin), int(w * (1 - 2 * margin)), int(h * (1 - 2 * margin)))
    mask = np.zeros((h, w), np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, rect, bgd, fgd, iters, cv2.GC_INIT_WITH_RECT)
    return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    images = sorted(
        p for p in Path(args.images).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not images:
        raise SystemExit(f"no images in {args.images}")

    flagged = []
    for p in images:
        bgr = cv2.imread(str(p))
        m = grabcut_mask(bgr)
        cv2.imwrite(str(out / f"{p.stem}.png"), m)
        frac = (m > 0).mean()
        tag = ""
        if frac < 0.03 or frac > 0.9:
            flagged.append(p.name)
            tag = "  <-- CHECK (coverage looks wrong)"
        print(f"{p.name}: product coverage {frac:.1%}{tag}")

    print(f"\nwrote {len(images)} rough masks to {out}")
    print("NEXT: hand-correct every mask in an image editor before running segmentation_iou.py")
    if flagged:
        print("Least confident:", ", ".join(flagged))


if __name__ == "__main__":
    main()
