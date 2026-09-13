"""Local CPU smoke test for the real SAM2 pipeline - NOT a metric run.

Purpose: prove the real `sam2_pipeline.SAM2Pipeline` code path (model load,
predictor, mask cleanup, unsegmentable guard) actually executes, before
spending Colab GPU time on it. Uses the tiny checkpoint so it finishes in
seconds on CPU. Produces no IoU/CLIP/SSIM numbers - there is no ground truth
here and these are not product photos.

Usage:
    curl -o models/sam2.1_hiera_tiny.pt \
      https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt
    python -m eval.smoke_test_sam2_cpu --images ../backend/uploads/1 --out eval/local_smoke_test
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from PIL import Image

from app.pipelines.sam2_pipeline import SAM2Pipeline, UnsegmentableImageError


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--checkpoint", default="models/sam2.1_hiera_tiny.pt")
    ap.add_argument("--config", default="configs/sam2.1/sam2.1_hiera_t.yaml")
    ap.add_argument("--out", default="eval/local_smoke_test")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pipe = SAM2Pipeline(checkpoint_path=args.checkpoint, model_cfg=args.config, device="cpu")

    for img_path in sorted(Path(args.images).iterdir()):
        if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        image = Image.open(img_path).convert("RGB")
        t0 = time.perf_counter()
        try:
            mask = pipe.segment(image)
            dt = time.perf_counter() - t0
            print(f"{img_path.name}: OK coverage={mask.mean():.1%} time={dt:.1f}s (CPU, tiny model)")
            cutout = pipe.remove_background(image)
            cutout.save(out / f"{img_path.stem}__sam2_real_cutout.png")
        except UnsegmentableImageError as exc:
            dt = time.perf_counter() - t0
            print(f"{img_path.name}: UNSEGMENTABLE ({exc}) time={dt:.1f}s")

    print(f"\nwrote cutouts to {out}. This is a code-path smoke test, not a metric run - see docs/HONESTY_REPORT.md.")


if __name__ == "__main__":
    main()
