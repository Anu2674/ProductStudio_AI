"""Real product segmentation with Meta's SAM2 (Segment Anything Model 2).

Uses the official ``sam2`` package (``pip install
git+https://github.com/facebookresearch/sam2.git``). Weights load lazily on the
first call so importing this module never needs torch, sam2, or a GPU.

Segmentation strategy for an unattended product photo (no user clicks):
  1. seed one positive point at the image centre (the product is almost always
     roughly centred in an e-commerce shot),
  2. seed four negative points near the corners (background),
  3. ask SAM2 for multiple mask hypotheses, keep the highest-scoring one,
  4. keep only the largest connected component and fill interior holes,
  5. reject the result if it covers ~the whole frame or ~nothing (unsegmentable).
"""

from __future__ import annotations

import numpy as np
from PIL import Image


class UnsegmentableImageError(RuntimeError):
    """SAM2 could not find a plausible single foreground object."""


class SAM2Pipeline:
    requires_mask = False

    def __init__(
        self,
        checkpoint_path: str,
        model_cfg: str,
        device: str = "cuda",
        min_mask_fraction: float = 0.01,
        max_mask_fraction: float = 0.97,
        min_score: float = 0.55,
    ):
        self.checkpoint_path = checkpoint_path
        self.model_cfg = model_cfg
        self.device = _resolve_device(device)
        self.min_mask_fraction = min_mask_fraction
        self.max_mask_fraction = max_mask_fraction
        self.min_score = min_score
        self._predictor = None

    # ------------------------------------------------------------------ loading
    def _load(self):
        if self._predictor is None:
            import torch
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            model = build_sam2(self.model_cfg, self.checkpoint_path, device=self.device)
            self._predictor = SAM2ImagePredictor(model)
            self._torch = torch
        return self._predictor

    # ------------------------------------------------------------------ public
    def segment(self, image: Image.Image) -> np.ndarray:
        """Return a boolean HxW mask, True where the product is."""
        predictor = self._load()
        rgb = np.array(image.convert("RGB"))
        h, w = rgb.shape[:2]

        point_coords = np.array(
            [
                [w * 0.5, h * 0.5],
                [w * 0.5, h * 0.62],
                [w * 0.5, h * 0.38],
                [w * 0.03, h * 0.03],
                [w * 0.97, h * 0.03],
                [w * 0.03, h * 0.97],
                [w * 0.97, h * 0.97],
            ],
            dtype=np.float32,
        )
        point_labels = np.array([1, 1, 1, 0, 0, 0, 0], dtype=np.int32)

        ctx = (
            self._torch.autocast(self.device, dtype=self._torch.bfloat16)
            if self.device == "cuda"
            else _nullcontext()
        )
        with self._torch.inference_mode(), ctx:
            predictor.set_image(rgb)
            masks, scores, _ = predictor.predict(
                point_coords=point_coords,
                point_labels=point_labels,
                multimask_output=True,
            )

        best = int(np.argmax(scores))
        score = float(scores[best])
        mask = masks[best].astype(bool)
        mask = _largest_component(mask)
        mask = _fill_holes(mask)

        frac = mask.mean()
        if score < self.min_score or frac < self.min_mask_fraction or frac > self.max_mask_fraction:
            raise UnsegmentableImageError(
                f"no clear foreground (score={score:.2f}, coverage={frac:.1%})"
            )
        return mask

    def remove_background(self, image: Image.Image) -> Image.Image:
        """RGBA cutout: product kept, background made transparent."""
        mask = self.segment(image)
        rgba = np.array(image.convert("RGBA"))
        rgba[..., 3] = (mask * 255).astype(np.uint8)
        return Image.fromarray(rgba)


# ---------------------------------------------------------------------- helpers
def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001
        return "cpu"


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


def _largest_component(mask: np.ndarray) -> np.ndarray:
    try:
        from scipy import ndimage

        labelled, n = ndimage.label(mask)
        if n <= 1:
            return mask
        sizes = ndimage.sum(mask, labelled, range(1, n + 1))
        keep = int(np.argmax(sizes)) + 1
        return labelled == keep
    except Exception:  # noqa: BLE001 - scipy optional
        return mask


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    try:
        from scipy import ndimage

        return ndimage.binary_fill_holes(mask)
    except Exception:  # noqa: BLE001
        return mask
