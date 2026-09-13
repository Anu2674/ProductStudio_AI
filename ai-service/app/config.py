from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "mock"  -> PIL placeholder (no torch models, boots anywhere, used by CI/tests)
    # "real"  -> SAM2 + SDXL-inpaint + ControlNet (needs GPU / Colab)
    PIPELINE_MODE: str = "mock"

    DEVICE: str = "cuda"  # "cuda" | "cpu" | "auto"

    # --- SAM2 (segmentation) ---
    # model size drives which checkpoint/config to use: tiny | small | base_plus | large
    SAM2_MODEL_SIZE: str = "small"
    SAM2_CHECKPOINT_PATH: str = "/models/sam2.1_hiera_small.pt"
    SAM2_MODEL_CONFIG: str = "configs/sam2.1/sam2.1_hiera_s.yaml"
    # reject a "segmentation" that is basically the whole frame or basically nothing
    SAM2_MIN_MASK_FRACTION: float = 0.01
    SAM2_MAX_MASK_FRACTION: float = 0.97
    SAM2_MIN_SCORE: float = 0.55

    # --- SDXL inpainting + ControlNet (background generation) ---
    SDXL_INPAINT_MODEL_ID: str = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
    CONTROLNET_TYPE: str = "canny"  # "canny" | "depth"
    CONTROLNET_CANNY_MODEL_ID: str = "diffusers/controlnet-canny-sdxl-1.0"
    CONTROLNET_DEPTH_MODEL_ID: str = "diffusers/controlnet-depth-sdxl-1.0"
    SDXL_STEPS: int = 25
    SDXL_GUIDANCE_SCALE: float = 7.0
    SDXL_CONTROLNET_SCALE: float = 0.55
    SDXL_TARGET_SIZE: int = 1024
    SDXL_MASK_DILATION_PX: int = 12  # grow product mask before inverting -> no bg halo
    # turn on for <12GB VRAM: sequential CPU offload + VAE tiling/slicing (slow but fits)
    LOW_VRAM: bool = False


settings = Settings()
