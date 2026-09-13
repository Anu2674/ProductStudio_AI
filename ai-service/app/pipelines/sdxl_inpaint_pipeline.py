"""Background generation with SDXL inpainting + ControlNet.

Given a product photo, the SAM2 product mask, and a text prompt, this regenerates
ONLY the background:

  * mask_image  = inverted (dilated) product mask  -> SDXL repaints the background,
    the product region is marked "keep".
  * control_image = Canny edges (or depth) of the original photo -> ControlNet
    conditions the diffusion so it does not hallucinate structure across the
    product silhouette.
  * after diffusion the product pixels are hard-composited back from the original
    with a feathered seam, so the product is guaranteed pixel-faithful regardless
    of any VAE drift at the mask boundary.

Weights load lazily. Needs a CUDA GPU in practice (SDXL). Set LOW_VRAM=true to fit
~8-12GB via sequential CPU offload + VAE tiling (much slower). 4GB is not enough
even then - use Colab; see notebooks/ProductStudio_AI_Pipeline_Colab.ipynb.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


class SDXLInpaintControlNetPipeline:
    requires_mask = True

    def __init__(
        self,
        inpaint_model_id: str,
        controlnet_type: str = "canny",
        controlnet_canny_id: str = "diffusers/controlnet-canny-sdxl-1.0",
        controlnet_depth_id: str = "diffusers/controlnet-depth-sdxl-1.0",
        device: str = "cuda",
        steps: int = 25,
        guidance_scale: float = 7.0,
        controlnet_scale: float = 0.55,
        target_size: int = 1024,
        mask_dilation_px: int = 12,
        low_vram: bool = False,
    ):
        self.inpaint_model_id = inpaint_model_id
        self.controlnet_type = controlnet_type
        self.controlnet_canny_id = controlnet_canny_id
        self.controlnet_depth_id = controlnet_depth_id
        self.device = _resolve_device(device)
        self.steps = steps
        self.guidance_scale = guidance_scale
        self.controlnet_scale = controlnet_scale
        self.target_size = target_size
        self.mask_dilation_px = mask_dilation_px
        self.low_vram = low_vram
        self._pipe = None
        self._depth = None

    # ------------------------------------------------------------------ loading
    def _load(self):
        if self._pipe is not None:
            return self._pipe
        import torch
        from diffusers import ControlNetModel, StableDiffusionXLControlNetInpaintPipeline

        dtype = torch.float16 if self.device == "cuda" else torch.float32
        cn_id = (
            self.controlnet_depth_id
            if self.controlnet_type == "depth"
            else self.controlnet_canny_id
        )
        controlnet = ControlNetModel.from_pretrained(cn_id, torch_dtype=dtype)
        pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
            self.inpaint_model_id, controlnet=controlnet, torch_dtype=dtype, variant=None
        )
        pipe.set_progress_bar_config(disable=True)

        if self.device == "cuda" and self.low_vram:
            # <10GB VRAM: keep weights on CPU RAM, stream to GPU layer by layer.
            # Trades speed for VRAM - but costs a lot of *system* RAM instead,
            # which is the scarcer resource on a free Colab T4 (12-13GB system
            # RAM vs 15GB VRAM). Only use this path on genuinely small GPUs.
            _try_enable(pipe, "enable_sequential_cpu_offload")
            _try_enable(pipe, "enable_vae_tiling")
            _try_enable(pipe, "enable_vae_slicing")
        elif self.device == "cuda":
            # Plenty of VRAM (e.g. a 15-16GB T4): load the whole pipeline onto
            # the GPU directly. enable_model_cpu_offload() was tried here first
            # and silently OOM-killed the process on Colab's free tier - it
            # shifts memory pressure onto system RAM (~12GB), which is smaller
            # than the GPU's VRAM here, so it made things worse, not better.
            pipe.to("cuda")
            _try_enable(pipe, "enable_vae_slicing")
        else:
            pipe.to("cpu")

        _try_enable(pipe, "enable_xformers_memory_efficient_attention")

        self._torch = torch
        self._pipe = pipe
        return pipe

    # ------------------------------------------------------------------ public
    def generate(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        product_mask: np.ndarray | None = None,
        seed: int | None = None,
    ) -> Image.Image:
        if product_mask is None:
            raise ValueError("SDXLInpaintControlNetPipeline.generate() requires product_mask")

        pipe = self._load()
        original = image.convert("RGB")
        w0, h0 = original.size

        work = _resize_to(original, self.target_size)
        tw, th = work.size
        mask_bool = _resize_mask(product_mask, (tw, th))

        bg_to_paint = _invert_dilated(mask_bool, self.mask_dilation_px)
        mask_image = Image.fromarray((bg_to_paint * 255).astype(np.uint8))
        control_image = self._control_image(work, mask_bool)

        generator = None
        if seed is not None:
            generator = self._torch.Generator(
                device="cuda" if self.device == "cuda" else "cpu"
            ).manual_seed(seed)

        full_negative = ", ".join(
            p for p in [negative_prompt, "warped product, distorted product, extra objects"] if p
        )

        out = pipe(
            prompt=prompt,
            negative_prompt=full_negative,
            image=work,
            mask_image=mask_image,
            control_image=control_image,
            num_inference_steps=self.steps,
            guidance_scale=self.guidance_scale,
            controlnet_conditioning_scale=self.controlnet_scale,
            strength=0.99,
            generator=generator,
        ).images[0]

        composited = _feathered_composite(work, out, mask_bool)
        return composited.resize((w0, h0), Image.LANCZOS)

    # ------------------------------------------------------------------ control
    def _control_image(self, work: Image.Image, mask_bool: np.ndarray) -> Image.Image:
        if self.controlnet_type == "depth":
            return self._depth_map(work)
        return _canny(work)

    def _depth_map(self, work: Image.Image) -> Image.Image:
        if self._depth is None:
            from controlnet_aux import MidasDetector

            self._depth = MidasDetector.from_pretrained("lllyasviel/Annotators")
        return self._depth(work).resize(work.size)


# ---------------------------------------------------------------------- helpers
def _try_enable(pipe, method_name: str) -> None:
    """Call an optional memory/speed optimization on a diffusers pipeline.

    Not every pipeline subclass implements every `enable_*` method (hit in
    practice: `StableDiffusionXLControlNetInpaintPipeline` in diffusers 0.30.3
    has no `enable_vae_slicing`). Skip silently-but-visibly rather than crash -
    these are optimizations, not correctness requirements.
    """
    method = getattr(pipe, method_name, None)
    if method is None:
        print(f"note: {type(pipe).__name__} has no {method_name}(), skipping")
        return
    try:
        method()
    except Exception as exc:  # noqa: BLE001 - best-effort optimization
        print(f"note: {method_name}() failed ({exc}), skipping")


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001
        return "cpu"


def _round8(x: int) -> int:
    return max(8, int(round(x / 8)) * 8)


def _resize_to(image: Image.Image, target_long: int) -> Image.Image:
    w, h = image.size
    scale = target_long / max(w, h)
    return image.resize((_round8(w * scale), _round8(h * scale)), Image.LANCZOS)


def _resize_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    m = Image.fromarray((mask.astype(np.uint8) * 255)).resize(size, Image.NEAREST)
    return np.array(m) > 127


def _invert_dilated(mask_bool: np.ndarray, dilation_px: int) -> np.ndarray:
    grown = mask_bool
    if dilation_px > 0:
        try:
            from scipy import ndimage

            grown = ndimage.binary_dilation(mask_bool, iterations=int(dilation_px))
        except Exception:  # noqa: BLE001
            grown = mask_bool
    return ~grown


def _canny(image: Image.Image) -> Image.Image:
    import cv2

    arr = np.array(image.convert("RGB"))
    edges = cv2.Canny(arr, 100, 200)
    return Image.fromarray(np.stack([edges] * 3, axis=-1))


def _feathered_composite(
    original: Image.Image, generated: Image.Image, mask_bool: np.ndarray, feather_px: int = 3
) -> Image.Image:
    alpha = Image.fromarray((mask_bool.astype(np.uint8) * 255))
    if feather_px > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather_px))
    a = np.array(alpha, dtype=np.float32)[..., None] / 255.0
    o = np.array(original.convert("RGB"), dtype=np.float32)
    g = np.array(generated.convert("RGB").resize(original.size), dtype=np.float32)
    out = o * a + g * (1.0 - a)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
