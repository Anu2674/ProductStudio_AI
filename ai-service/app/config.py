from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SAM2_CHECKPOINT_PATH: str = "/models/sam2_hiera_large.pt"
    SAM2_MODEL_CONFIG: str = "sam2_hiera_l.yaml"
    SDXL_BASE_MODEL_ID: str = "stabilityai/stable-diffusion-xl-base-1.0"
    SDXL_CONTROLNET_MODEL_ID: str = "diffusers/controlnet-canny-sdxl-1.0"
    DEVICE: str = "cuda"


settings = Settings()
