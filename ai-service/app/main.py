import io

import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

from app.config import settings
from app.pipelines import build_generation_pipeline, build_segmentation_pipeline

app = FastAPI(title="ProductStudio AI - Inference Service")

_segmentation_pipeline = build_segmentation_pipeline(settings)
_generation_pipeline = build_generation_pipeline(settings)


def get_segmentation_pipeline():
    return _segmentation_pipeline


def get_generation_pipeline():
    return _generation_pipeline


def _read_image(content: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(content))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid image: {exc}") from exc


def _png_response(image: Image.Image) -> Response:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


def _unsegmentable(exc: Exception) -> bool:
    return exc.__class__.__name__ == "UnsegmentableImageError"


@app.get("/health")
def health_check():
    return {"status": "ok", "pipeline_mode": settings.PIPELINE_MODE, "device": settings.DEVICE}


@app.post("/segment")
async def segment(file: UploadFile = File(...), pipeline=Depends(get_segmentation_pipeline)):
    image = _read_image(await file.read())
    try:
        result = pipeline.remove_background(image)
    except Exception as exc:  # noqa: BLE001
        if _unsegmentable(exc):
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise
    return _png_response(result)


@app.post("/segment/mask")
async def segment_mask(file: UploadFile = File(...), pipeline=Depends(get_segmentation_pipeline)):
    """Single-channel (L) mask PNG, white = product. Used by the eval harness."""
    image = _read_image(await file.read())
    try:
        mask = pipeline.segment(image)
    except Exception as exc:  # noqa: BLE001
        if _unsegmentable(exc):
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise
    mask_img = Image.fromarray((np.asarray(mask).astype(np.uint8) * 255))
    return _png_response(mask_img)


@app.post("/generate")
async def generate(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    seg_pipeline=Depends(get_segmentation_pipeline),
    gen_pipeline=Depends(get_generation_pipeline),
):
    image = _read_image(await file.read())

    product_mask = None
    if getattr(gen_pipeline, "requires_mask", False):
        try:
            product_mask = seg_pipeline.segment(image)
        except Exception as exc:  # noqa: BLE001
            if _unsegmentable(exc):
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            raise

    result = gen_pipeline.generate(image, prompt, negative_prompt, product_mask=product_mask)
    return _png_response(result)
