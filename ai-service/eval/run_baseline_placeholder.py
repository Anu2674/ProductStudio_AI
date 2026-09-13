"""Phase 0 - Honest baseline capture.

Runs the OLD PIL/NumPy placeholder pipeline (mock_pipeline.py) on a folder of
images and saves the outputs. This is the "before" reference so any improvement
from the real SAM2 + SDXL pipeline can be shown honestly side by side.

This script deliberately imports the placeholder directly - it is NOT a model and
is being retired. Do not wire it into anything new.

Usage:
    python -m eval.run_baseline_placeholder --src ../backend/uploads/1 --out eval/baseline_placeholder
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from PIL import Image

from app.pipelines.mock_pipeline import SAM2Pipeline as PlaceholderSeg
from app.pipelines.mock_pipeline import SDXLControlNetPipeline as PlaceholderGen

PROMPTS = [
    "product on a clean white studio background, soft lighting",
    "product on a warm wooden table, golden hour light",
    "product on a blue gradient background, bright and professional",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="folder of source images")
    parser.add_argument("--out", required=True, help="folder to write placeholder outputs")
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    seg = PlaceholderSeg()
    gen = PlaceholderGen()

    images = sorted(p for p in src.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not images:
        raise SystemExit(f"no images found in {src}")

    rows = []
    for img_path in images:
        image = Image.open(img_path).convert("RGB")

        t0 = time.perf_counter()
        seg_out = seg.remove_background(image)
        seg_ms = (time.perf_counter() - t0) * 1000
        seg_out.save(out / f"{img_path.stem}__placeholder_segment.png")

        prompt = PROMPTS[len(rows) % len(PROMPTS)]
        t0 = time.perf_counter()
        gen_out = gen.generate(image, prompt, "")
        gen_ms = (time.perf_counter() - t0) * 1000
        gen_out.save(out / f"{img_path.stem}__placeholder_generate.png")

        rows.append((img_path.name, image.size, prompt, seg_ms, gen_ms))
        print(f"{img_path.name}: seg {seg_ms:.1f} ms, gen {gen_ms:.1f} ms  prompt={prompt!r}")

    report = out / "BASELINE_NOTES.md"
    with report.open("w", encoding="utf-8") as f:
        f.write("# Phase 0 baseline - PLACEHOLDER pipeline outputs\n\n")
        f.write("These outputs come from `mock_pipeline.py` (PIL brightness thresholding + ")
        f.write("color fill). No neural network is involved. Kept only as a 'before' reference.\n\n")
        f.write("| image | size | prompt | seg time | gen time |\n")
        f.write("|---|---|---|---|---|\n")
        for name, size, prompt, seg_ms, gen_ms in rows:
            f.write(f"| {name} | {size[0]}x{size[1]} | {prompt} | {seg_ms:.1f} ms | {gen_ms:.1f} ms |\n")
        f.write("\n**What the placeholder does wrong (why it must be replaced):**\n\n")
        f.write("- 'Segmentation' is `brightness > 200` - it does not find the product, ")
        f.write("it finds bright pixels. Any product on a non-white background fails completely.\n")
        f.write("- 'Background generation' is `pixels brighter than 180 := solid color` plus a ")
        f.write("global brightness/contrast tweak. It cannot render a scene, honor a text prompt, ")
        f.write("or respect the product's shape.\n")
        f.write("- Timings above are CPU milliseconds because there is no model to run.\n")
    print(f"\nwrote {report}")


if __name__ == "__main__":
    main()
