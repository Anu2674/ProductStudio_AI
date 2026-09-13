"""Unit tests for the real SAM2 / SDXL-inpaint pipelines.

These do NOT download or run any model weights. They monkeypatch the lazy
``_load()`` step with fakes and exercise the pre/post-processing that is entirely
our own code: mask shape, connected-component cleanup, the unsegmentable guard,
output dimensions, and product-region preservation.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from app.pipelines.sam2_pipeline import SAM2Pipeline, UnsegmentableImageError
from app.pipelines.sdxl_inpaint_pipeline import (
    SDXLInpaintControlNetPipeline,
    _feathered_composite,
    _invert_dilated,
    _resize_mask,
    _resize_to,
    _round8,
)


# ------------------------------------------------------------------ SAM2 fakes
class _FakePredictor:
    """Returns a centred rectangular mask plus a spurious speck, high score."""

    def __init__(self, h, w):
        self.h, self.w = h, w

    def set_image(self, rgb):  # noqa: D401
        pass

    def predict(self, point_coords, point_labels, multimask_output):
        m = np.zeros((self.h, self.w), dtype=bool)
        m[self.h // 4 : 3 * self.h // 4, self.w // 4 : 3 * self.w // 4] = True
        m[0:2, 0:2] = True  # detached speck -> must be dropped by _largest_component
        weak = np.zeros((self.h, self.w), dtype=bool)
        return np.stack([m, weak, weak]), np.array([0.92, 0.10, 0.05]), None


class _AllTruePredictor(_FakePredictor):
    def predict(self, point_coords, point_labels, multimask_output):
        full = np.ones((self.h, self.w), dtype=bool)
        return np.stack([full, full, full]), np.array([0.99, 0.9, 0.8]), None


def _patch_sam(monkeypatch, predictor):
    import types

    def fake_load(self):
        self._torch = types.SimpleNamespace(
            autocast=lambda *a, **k: _Null(),
            inference_mode=lambda: _Null(),
        )
        self._predictor = predictor
        return predictor

    monkeypatch.setattr(SAM2Pipeline, "_load", fake_load)


class _Null:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


# ------------------------------------------------------------------ SAM2 tests
def test_segment_returns_bool_mask_matching_image_shape(monkeypatch):
    img = Image.new("RGB", (200, 120), "white")
    _patch_sam(monkeypatch, _FakePredictor(120, 200))
    pipe = SAM2Pipeline("x", "y", device="cpu")

    mask = pipe.segment(img)

    assert mask.dtype == bool
    assert mask.shape == (120, 200)  # (H, W), matches PIL (W, H)


def test_segment_keeps_only_largest_component(monkeypatch):
    img = Image.new("RGB", (200, 120), "white")
    _patch_sam(monkeypatch, _FakePredictor(120, 200))
    pipe = SAM2Pipeline("x", "y", device="cpu")

    mask = pipe.segment(img)

    assert not mask[0:2, 0:2].any()  # the detached speck is gone
    assert mask[60, 100]  # centre kept


def test_unsegmentable_image_raises(monkeypatch):
    img = Image.new("RGB", (200, 120), "white")
    _patch_sam(monkeypatch, _AllTruePredictor(120, 200))
    pipe = SAM2Pipeline("x", "y", device="cpu", max_mask_fraction=0.97)

    with pytest.raises(UnsegmentableImageError):
        pipe.segment(img)


def test_remove_background_returns_rgba_same_size(monkeypatch):
    img = Image.new("RGB", (200, 120), "white")
    _patch_sam(monkeypatch, _FakePredictor(120, 200))
    pipe = SAM2Pipeline("x", "y", device="cpu")

    out = pipe.remove_background(img)

    assert out.mode == "RGBA"
    assert out.size == (200, 120)


# ------------------------------------------------------------- SDXL helper tests
def test_round8():
    assert _round8(1023) == 1024
    assert _round8(100) == 96
    assert _round8(1) == 8


def test_resize_to_keeps_aspect_and_multiple_of_8():
    img = Image.new("RGB", (1600, 1200), "white")
    out = _resize_to(img, 1024)
    assert max(out.size) == 1024
    assert out.size[0] % 8 == 0 and out.size[1] % 8 == 0
    assert abs((out.size[0] / out.size[1]) - (1600 / 1200)) < 0.05


def test_resize_mask_shape_and_dtype():
    mask = np.zeros((120, 200), dtype=bool)
    mask[30:90, 50:150] = True
    out = _resize_mask(mask, (100, 60))
    assert out.shape == (60, 100)
    assert out.dtype == bool
    assert out.any()


def test_invert_dilated_flips_and_grows():
    mask = np.zeros((50, 50), dtype=bool)
    mask[20:30, 20:30] = True
    bg = _invert_dilated(mask, dilation_px=2)
    assert bg[0, 0]  # background stays background
    assert not bg[25, 25]  # product centre excluded from repaint


def test_feathered_composite_preserves_product_pixels_exactly():
    original = Image.new("RGB", (40, 40), (10, 20, 30))
    generated = Image.new("RGB", (40, 40), (200, 200, 200))
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:30, 10:30] = True

    out = np.array(_feathered_composite(original, generated, mask, feather_px=0))

    assert (out[15:25, 15:25] == (10, 20, 30)).all()  # product untouched
    assert (out[0:5, 0:5] == (200, 200, 200)).all()  # background replaced


# ------------------------------------------------------------- SDXL generate test
class _FakeInpaintPipe:
    def set_progress_bar_config(self, **_):
        pass

    def __call__(self, *, image, mask_image, **kw):
        # pretend the model repainted everything grey
        grey = Image.new("RGB", image.size, (128, 128, 128))
        return type("R", (), {"images": [grey]})()


def test_generate_output_matches_input_size_and_keeps_product(monkeypatch):
    import types

    original = Image.new("RGB", (300, 200), (0, 0, 255))
    mask = np.zeros((200, 300), dtype=bool)
    mask[50:150, 100:200] = True

    pipe = SDXLInpaintControlNetPipeline("m", controlnet_type="canny", device="cpu")

    def fake_load(self):
        self._torch = types.SimpleNamespace(Generator=lambda **k: types.SimpleNamespace(manual_seed=lambda s: None))
        self._pipe = _FakeInpaintPipe()
        return self._pipe

    monkeypatch.setattr(SDXLInpaintControlNetPipeline, "_load", fake_load)
    monkeypatch.setattr(
        "app.pipelines.sdxl_inpaint_pipeline._canny",
        lambda img: Image.new("RGB", img.size, (0, 0, 0)),
    )

    out = pipe.generate(original, "a sunny beach", "", product_mask=mask)

    assert out.size == (300, 200)  # same as input
    arr = np.array(out)
    assert (arr[90:110, 140:160] == (0, 0, 255)).all()  # product pixels preserved
    assert tuple(arr[5, 5]) != (0, 0, 255)  # background changed


def test_generate_without_mask_raises():
    pipe = SDXLInpaintControlNetPipeline("m", device="cpu")
    with pytest.raises(ValueError):
        pipe.generate(Image.new("RGB", (10, 10)), "prompt", "", product_mask=None)
