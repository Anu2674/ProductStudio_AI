import io

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.responses import Response
from PIL import Image

from app.config import settings
from app.pipelines.sam2_pipeline import SAM2Pipeline
from app.pipelines.sdxl_pipeline import SDXLControlNetPipeline

app = FastAPI(title="ProductStudio AI - Inference Service")

_segmentation_pipeline = SAM2Pipeline(settings.SAM2_CHECKPOINT_PATH, settings.SAM2_MODEL_CONFIG, settings.DEVICE)
_generation_pipeline = SDXLControlNetPipeline(
    settings.SDXL_BASE_MODEL_ID, settings.SDXL_CONTROLNET_MODEL_ID, settings.DEVICE
)


def get_segmentation_pipeline() -> SAM2Pipeline:
    return _segmentation_pipeline


def get_generation_pipeline() -> SDXLControlNetPipeline:
    return _generation_pipeline


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/segment")
async def segment(file: UploadFile = File(...), pipeline=Depends(get_segmentation_pipeline)):
    content = await file.read()
    image = Image.open(io.BytesIO(content))
    result = pipeline.remove_background(image)
    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@app.post("/generate")
async def generate(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    pipeline=Depends(get_generation_pipeline),
):
    content = await file.read()
    image = Image.open(io.BytesIO(content))
    result = pipeline.generate(image, prompt, negative_prompt)
    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")
