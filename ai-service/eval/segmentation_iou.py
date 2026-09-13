"""Phase 1 - real mean IoU of SAM2 masks vs hand-labelled ground truth.

Runs the real SAM2 pipeline on every image that has a matching ground-truth mask,
computes IoU and boundary-F1 per image, and writes a CSV plus a summary line.

Usage (needs requirements-eval.txt + a SAM2 checkpoint):
    python -m eval.segmentation_iou \
        --images eval/test_images --gt eval/ground_truth \
        --checkpoint /models/sam2.1_hiera_small.pt \
        --config configs/sam2.1/sam2.1_hiera_s.yaml \
        --device cuda --out eval/results/segmentation_iou.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image

from eval.metrics import boundary_f1, iou


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="eval/results/segmentation_iou.csv")
    args = ap.parse_args()

    from app.pipelines.sam2_pipeline import SAM2Pipeline, UnsegmentableImageError

    pipe = SAM2Pipeline(args.checkpoint, args.config, device=args.device)

    gt_dir = Path(args.gt)
    rows = []
    for img_path in sorted(Path(args.images).iterdir()):
        if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        gt_path = gt_dir / f"{img_path.stem}.png"
        if not gt_path.exists():
            print(f"skip {img_path.name} (no ground truth)")
            continue

        image = Image.open(img_path).convert("RGB")
        gt = np.array(Image.open(gt_path).convert("L")) > 127
        try:
            pred = pipe.segment(image)
            i = iou(pred, gt)
            b = boundary_f1(pred, gt)
            status = "ok"
        except UnsegmentableImageError as exc:
            i, b, status = 0.0, 0.0, f"unsegmentable: {exc}"
        rows.append({"image": img_path.name, "iou": round(i, 4), "boundary_f1": round(b, 4), "status": status})
        print(f"{img_path.name}: IoU={i:.4f}  bF1={b:.4f}  {status}")

    if not rows:
        raise SystemExit("no image/ground-truth pairs found")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["image", "iou", "boundary_f1", "status"])
        w.writeheader()
        w.writerows(rows)

    ious = [r["iou"] for r in rows]
    bf1s = [r["boundary_f1"] for r in rows]
    print("\n=== Phase 1 segmentation result (REAL) ===")
    print(f"images evaluated : {len(rows)}")
    print(f"mean IoU         : {np.mean(ious):.4f}")
    print(f"median IoU       : {np.median(ious):.4f}")
    print(f"min IoU          : {np.min(ious):.4f}")
    print(f"mean boundary F1 : {np.mean(bf1s):.4f}")
    print(f"csv              : {out}")


if __name__ == "__main__":
    main()
