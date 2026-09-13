"""Phase 2 + Phase 3 driver - runs the REAL pipeline and computes REAL metrics.

For every (image, prompt) in the manifest:
  1. SAM2 -> product mask                (timed)
  2. SDXL inpaint + ControlNet -> output (timed)
  3. CLIP score   : output image vs prompt        (text-image alignment)
  4. product SSIM : original vs output, product region only  (higher = preserved)
  5. product LPIPS: original vs output, product region only  (lower  = preserved)

Writes:
  results/generations/<stem>__out.png, __mask.png
  results/generation_metrics.csv
  results/RESULTS.md   (the table you cite - all numbers real)

Usage:
    python -m eval.run_eval \
        --images eval/test_images --manifest eval/prompts.json \
        --sam2-checkpoint /models/sam2.1_hiera_small.pt \
        --sam2-config configs/sam2.1/sam2.1_hiera_s.yaml \
        --device cuda --out eval/results
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import time
from pathlib import Path

import numpy as np
from PIL import Image

from eval.metrics import CLIPScorer, product_ssim

try:
    from eval.metrics import LPIPSScorer
except ImportError as exc:  # noqa: BLE001 - lpips is optional, see main()
    LPIPSScorer = None
    _LPIPS_IMPORT_ERROR = str(exc)

CLIP_FAIL_THRESHOLD = 20.0  # below this we flag the row as a failure case (shown, not hidden)


def _gpu_name(device: str) -> str:
    if device != "cuda":
        return f"CPU ({platform.processor() or platform.machine()})"
    import torch

    return torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cuda (unavailable)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sam2-checkpoint", required=True)
    ap.add_argument("--sam2-config", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--controlnet", default="canny", choices=["canny", "depth"])
    ap.add_argument("--low-vram", action="store_true")
    ap.add_argument("--out", default="eval/results")
    args = ap.parse_args()

    from app.config import settings
    from app.pipelines.sam2_pipeline import SAM2Pipeline, UnsegmentableImageError
    from app.pipelines.sdxl_inpaint_pipeline import SDXLInpaintControlNetPipeline

    out = Path(args.out)
    (out / "generations").mkdir(parents=True, exist_ok=True)

    seg = SAM2Pipeline(args.sam2_checkpoint, args.sam2_config, device=args.device)
    gen = SDXLInpaintControlNetPipeline(
        inpaint_model_id=settings.SDXL_INPAINT_MODEL_ID,
        controlnet_type=args.controlnet,
        device=args.device,
        low_vram=args.low_vram,
    )
    clip = CLIPScorer(device=args.device if args.device == "cuda" else "cpu")
    lpips_scorer = None
    if LPIPSScorer is not None:
        try:
            lpips_scorer = LPIPSScorer(device=args.device if args.device == "cuda" else "cpu")
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: lpips unavailable ({exc}) - continuing without product LPIPS")
    else:
        print(f"WARNING: lpips not installed ({_LPIPS_IMPORT_ERROR}) - continuing without product LPIPS")

    manifest = json.loads(Path(args.manifest).read_text())
    rows = []

    for entry in manifest:
        img_path = Path(args.images) / entry["image"]
        if not img_path.exists():
            print(f"skip {entry['image']} (missing)")
            continue
        image = Image.open(img_path).convert("RGB")
        prompt = entry["prompt"]
        negative = entry.get("negative_prompt", "")
        seed = entry.get("seed")

        try:
            t0 = time.perf_counter()
            mask = seg.segment(image)
            seg_s = time.perf_counter() - t0
        except UnsegmentableImageError as exc:
            print(f"{entry['image']}: UNSEGMENTABLE - {exc}")
            rows.append(
                {
                    "image": entry["image"], "prompt": prompt, "seg_s": 0.0, "gen_s": 0.0,
                    "clip_score": 0.0, "product_ssim": 0.0,
                    "product_lpips": (1.0 if lpips_scorer else None),
                    "note": "unsegmentable",
                }
            )
            _write_csv(out / "generation_metrics.csv", rows)
            _write_results_md(out / "RESULTS.md", rows, _gpu_name(args.device), args)
            continue

        t0 = time.perf_counter()
        result = gen.generate(image, prompt, negative, product_mask=mask, seed=seed)
        gen_s = time.perf_counter() - t0

        stem = img_path.stem
        result.save(out / "generations" / f"{stem}__out.png")
        Image.fromarray((mask.astype(np.uint8) * 255)).save(out / "generations" / f"{stem}__mask.png")

        clip_score = clip.score(result, prompt)
        ssim = product_ssim(image, result, mask)
        lp = lpips_scorer.distance(image, result, mask) if lpips_scorer else None
        note = "FAILURE CASE (low CLIP)" if clip_score < CLIP_FAIL_THRESHOLD else ""

        rows.append(
            {
                "image": entry["image"], "prompt": prompt,
                "seg_s": round(seg_s, 3), "gen_s": round(gen_s, 3),
                "clip_score": round(clip_score, 2),
                "product_ssim": round(ssim, 4),
                "product_lpips": (round(lp, 4) if lp is not None else None),
                "note": note,
            }
        )
        lp_str = f"{lp:.4f}" if lp is not None else "n/a"
        print(
            f"{entry['image']}: CLIP={clip_score:.2f} SSIM={ssim:.4f} LPIPS={lp_str} "
            f"seg={seg_s:.2f}s gen={gen_s:.2f}s {note}"
        )

        # Write after every single image, not just at the end - a run that gets cut
        # off (Colab disconnect, OOM, etc.) still leaves everything done so far on
        # disk instead of losing the whole run's work.
        _write_csv(out / "generation_metrics.csv", rows)
        _write_results_md(out / "RESULTS.md", rows, _gpu_name(args.device), args)
        print(f"  [{len(rows)}/{len(manifest)}] saved so far -> {out / 'RESULTS.md'}")

    if not rows:
        raise SystemExit("nothing evaluated - check --images / --manifest")

    print(f"\nDONE - wrote {out/'RESULTS.md'} and {out/'generation_metrics.csv'} ({len(rows)} images)")


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _mean(rows, key, where=lambda r: True):
    vals = [r[key] for r in rows if where(r) and r.get(key) is not None]
    return float(np.mean(vals)) if vals else None


def _fmt(value, decimals: int = 4) -> str:
    return f"{value:.{decimals}f}" if value is not None else "n/a (lpips unavailable)"


def _write_results_md(path: Path, rows: list[dict], gpu: str, args) -> None:
    ok = [r for r in rows if r["note"] != "unsegmentable"]
    mean_seg = _mean(ok, "seg_s") or 0.0
    mean_gen = _mean(ok, "gen_s") or 0.0
    lines = [
        "# ProductStudio AI - Phase 3 evaluation results (REAL RUN)",
        "",
        f"- pipeline: SAM2 ({Path(args.sam2_checkpoint).name}) + SDXL inpainting "
        f"({args.controlnet} ControlNet)",
        f"- hardware: {gpu}",
        f"- images evaluated: {len(rows)}  (unsegmentable: {len(rows) - len(ok)})",
        f"- generated: {__import__('datetime').date.today().isoformat()}",
        "",
        "## Summary",
        "",
        "| metric | mean | what it means |",
        "|---|---|---|",
        f"| CLIP score (output vs prompt) | {_fmt(_mean(ok, 'clip_score'), 2)} | text-image alignment, higher better |",
        f"| product SSIM (region) | {_fmt(_mean(ok, 'product_ssim'))} | product preserved, 1.0 = identical |",
        f"| product LPIPS (region) | {_fmt(_mean(ok, 'product_lpips'))} | product distortion, 0.0 = identical |",
        f"| segmentation latency | {_fmt(mean_seg, 2)} s | SAM2 per image |",
        f"| generation latency | {_fmt(mean_gen, 2)} s | SDXL inpaint per image |",
        f"| end-to-end latency | {_fmt(mean_seg + mean_gen, 2)} s | segment + generate |",
        "",
        "## Per-image",
        "",
        "| image | CLIP | SSIM | LPIPS | seg s | gen s | note |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lp_cell = r["product_lpips"] if r["product_lpips"] is not None else "n/a"
        lines.append(
            f"| {r['image']} | {r['clip_score']} | {r['product_ssim']} | {lp_cell} "
            f"| {r['seg_s']} | {r['gen_s']} | {r['note']} |"
        )
    lines += [
        "",
        "## Failure cases",
        "",
        "Rows marked FAILURE CASE above are kept deliberately. Inspect the matching "
        "`results/generations/<stem>__out.png` and describe why the prompt did not work "
        "(e.g. product recolored, background ignored the prompt, seam artifacts).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
