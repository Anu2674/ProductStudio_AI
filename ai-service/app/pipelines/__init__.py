"""Pipeline factory.

PIPELINE_MODE=mock  -> PIL placeholders (no torch models; CI/tests/local boot)
PIPELINE_MODE=real  -> SAM2 + SDXL-inpaint + ControlNet (GPU / Colab)
"""

from __future__ import annotations

from app.config import Settings


def build_segmentation_pipeline(settings: Settings):
    if settings.PIPELINE_MODE == "real":
        from app.pipelines.sam2_pipeline import SAM2Pipeline

        return SAM2Pipeline(
            checkpoint_path=settings.SAM2_CHECKPOINT_PATH,
            model_cfg=settings.SAM2_MODEL_CONFIG,
            device=settings.DEVICE,
            min_mask_fraction=settings.SAM2_MIN_MASK_FRACTION,
            max_mask_fraction=settings.SAM2_MAX_MASK_FRACTION,
            min_score=settings.SAM2_MIN_SCORE,
        )

    from app.pipelines.mock_pipeline import SAM2Pipeline as MockSAM2

    return MockSAM2()


def build_generation_pipeline(settings: Settings):
    if settings.PIPELINE_MODE == "real":
        from app.pipelines.sdxl_inpaint_pipeline import SDXLInpaintControlNetPipeline

        return SDXLInpaintControlNetPipeline(
            inpaint_model_id=settings.SDXL_INPAINT_MODEL_ID,
            controlnet_type=settings.CONTROLNET_TYPE,
            controlnet_canny_id=settings.CONTROLNET_CANNY_MODEL_ID,
            controlnet_depth_id=settings.CONTROLNET_DEPTH_MODEL_ID,
            device=settings.DEVICE,
            steps=settings.SDXL_STEPS,
            guidance_scale=settings.SDXL_GUIDANCE_SCALE,
            controlnet_scale=settings.SDXL_CONTROLNET_SCALE,
            target_size=settings.SDXL_TARGET_SIZE,
            mask_dilation_px=settings.SDXL_MASK_DILATION_PX,
            low_vram=settings.LOW_VRAM,
        )

    from app.pipelines.mock_pipeline import SDXLControlNetPipeline as MockGen

    return MockGen()
