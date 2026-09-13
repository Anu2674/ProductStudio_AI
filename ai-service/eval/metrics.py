"""Real metric implementations shared by the eval scripts.

All of these operate on numpy arrays / PIL images and return plain floats. No
estimates, no hardcoded numbers - every value comes from an actual computation on
actual images.
"""

from __future__ import annotations

import warnings

import numpy as np
from PIL import Image


# ----------------------------------------------------------------- segmentation
def _align_gt(pred: np.ndarray, gt: np.ndarray) -> np.ndarray:
    """Make a ground-truth mask's shape match the predicted mask's shape.

    Handles a real glitch we hit in practice: a hand-corrected mask PNG can come
    back rotated 90 degrees relative to its source photo (an image editor
    silently applying EXIF orientation the source photo doesn't carry). In that
    case we rotate (lossless) instead of resizing (which would stretch the
    content and quietly produce a wrong, misleading score). Any other shape
    mismatch falls back to a resize, with a warning so it isn't silently wrong.
    """
    if gt.shape == pred.shape:
        return gt
    if gt.shape == pred.shape[::-1]:
        warnings.warn(
            f"ground-truth mask is rotated 90 deg relative to the source image "
            f"(gt={gt.shape}, pred={pred.shape}) - auto-rotating to align. "
            f"Re-check this mask if the resulting score looks off.",
            stacklevel=2,
        )
        return np.rot90(gt)
    warnings.warn(
        f"ground-truth mask shape {gt.shape} does not match the source image "
        f"shape {pred.shape} - resizing (lossy). Re-export this mask at the "
        f"source image's exact resolution instead.",
        stacklevel=2,
    )
    return np.array(
        Image.fromarray(gt.astype(np.uint8) * 255).resize(
            (pred.shape[1], pred.shape[0]), Image.NEAREST
        )
    ) > 127


def iou(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float:
    """Intersection-over-Union between two boolean HxW masks."""
    pred = pred_mask.astype(bool)
    gt = _align_gt(pred, gt_mask.astype(bool))
    inter = np.logical_and(pred, gt).sum()
    union = np.logical_or(pred, gt).sum()
    return float(inter / union) if union else 0.0


def boundary_f1(pred_mask: np.ndarray, gt_mask: np.ndarray, tol_px: int = 3) -> float:
    """Boundary F-measure (how well mask edges line up), tolerance in pixels."""
    from scipy import ndimage

    pred = pred_mask.astype(bool)
    gt = _align_gt(pred, gt_mask.astype(bool))
    pe = pred ^ ndimage.binary_erosion(pred)
    ge = gt ^ ndimage.binary_erosion(gt)
    gt_dt = ndimage.distance_transform_edt(~ge)
    pred_dt = ndimage.distance_transform_edt(~pe)
    precision = (gt_dt[pe] <= tol_px).mean() if pe.any() else 0.0
    recall = (pred_dt[ge] <= tol_px).mean() if ge.any() else 0.0
    if precision + recall == 0:
        return 0.0
    return float(2 * precision * recall / (precision + recall))


# --------------------------------------------------------------- text alignment
class CLIPScorer:
    """CLIP score = 100 * cosine(text_embedding, image_embedding).

    Uses HuggingFace `transformers`' CLIP (openai/clip-vit-base-patch32) rather
    than the open-clip-torch package: open-clip-torch's pinned build repeatedly
    failed "metadata-generation" on a fresh Colab install in practice, while
    transformers is already a hard dependency of diffusers/SDXL and installs
    reliably. Same standard CLIP-score formula either way. Higher is better;
    for a well-matched caption expect roughly the low-to-mid 20s to low 30s.
    """

    def __init__(self, device: str = "cpu"):
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self.torch = torch
        self.device = device
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device).eval()
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    def score(self, image: Image.Image, text: str) -> float:
        inputs = self.processor(
            text=[text], images=image.convert("RGB"), return_tensors="pt", padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with self.torch.no_grad():
            out = self.model(**inputs)
        img_f = out.image_embeds / out.image_embeds.norm(dim=-1, keepdim=True)
        txt_f = out.text_embeds / out.text_embeds.norm(dim=-1, keepdim=True)
        return float((100.0 * (img_f * txt_f).sum(dim=-1)).clamp(min=0).item())


# ------------------------------------------------------- product preservation
def _bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    return int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1


def _product_crop(image: Image.Image, mask: np.ndarray) -> np.ndarray:
    arr = np.array(image.convert("RGB"))
    m = mask.astype(bool)
    arr = arr * m[..., None]  # zero out background so only the product contributes
    y0, y1, x0, x1 = _bbox(m)
    return arr[y0:y1, x0:x1]


def _ssim_channel(a: np.ndarray, b: np.ndarray, win_size: int = 7, data_range: float = 255.0) -> float:
    """Single-channel windowed SSIM (same formula skimage uses with uniform
    windows), implemented with scipy.ndimage so it needs no extra package.

    scikit-image's build repeatedly failed "metadata-generation" on a fresh
    Colab install in practice (a pip/build-toolchain issue, not specific to
    this package - open-clip-torch and lpips hit the identical failure in the
    same session). scipy is already a hard, reliably-installed dependency, so
    this reimplements the standard windowed-SSIM formula directly on top of it.
    """
    from scipy.ndimage import uniform_filter

    a = a.astype(np.float64)
    b = b.astype(np.float64)
    c1 = (0.01 * data_range) ** 2
    c2 = (0.03 * data_range) ** 2

    ux = uniform_filter(a, size=win_size)
    uy = uniform_filter(b, size=win_size)
    uxx = uniform_filter(a * a, size=win_size)
    uyy = uniform_filter(b * b, size=win_size)
    uxy = uniform_filter(a * b, size=win_size)
    vx = uxx - ux * ux
    vy = uyy - uy * uy
    vxy = uxy - ux * uy

    num = (2 * ux * uy + c1) * (2 * vxy + c2)
    den = (ux * ux + uy * uy + c1) * (vx + vy + c2)
    return float(np.mean(num / den))


def product_ssim(original: Image.Image, output: Image.Image, mask: np.ndarray) -> float:
    """SSIM over the product region only. 1.0 = identical, lower = more distortion."""
    a = _product_crop(original, mask)
    b = _product_crop(output.resize(original.size), mask)
    return float(np.mean([_ssim_channel(a[..., c], b[..., c]) for c in range(a.shape[-1])]))


class LPIPSScorer:
    """LPIPS perceptual distance over the product region. 0.0 = identical, lower better."""

    def __init__(self, device: str = "cpu"):
        import lpips
        import torch

        self.torch = torch
        self.device = device
        self.model = lpips.LPIPS(net="alex").to(device).eval()

    def distance(self, original: Image.Image, output: Image.Image, mask: np.ndarray) -> float:
        a = _product_crop(original, mask)
        b = _product_crop(output.resize(original.size), mask)

        def to_t(x):
            t = self.torch.from_numpy(x).float().permute(2, 0, 1).unsqueeze(0) / 127.5 - 1.0
            return t.to(self.device)

        with self.torch.no_grad():
            return float(self.model(to_t(a), to_t(b)).item())
