from PIL import Image


class SDXLControlNetPipeline:
    """Wraps SDXL + ControlNet (Canny) for controllable product photo generation.

    Conditioning on the Canny edge map of the source product photo preserves the
    product's silhouette while SDXL regenerates the background, lighting, and scene
    according to the prompt. Model weights load lazily - see SAM2Pipeline docstring.
    """

    def __init__(self, base_model_id: str, controlnet_model_id: str, device: str = "cuda"):
        self.base_model_id = base_model_id
        self.controlnet_model_id = controlnet_model_id
        self.device = device
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            import torch
            from diffusers import ControlNetModel, StableDiffusionXLControlNetPipeline

            controlnet = ControlNetModel.from_pretrained(self.controlnet_model_id, torch_dtype=torch.float16)
            self._pipeline = StableDiffusionXLControlNetPipeline.from_pretrained(
                self.base_model_id, controlnet=controlnet, torch_dtype=torch.float16
            ).to(self.device)
        return self._pipeline

    def _canny_edges(self, image: Image.Image) -> Image.Image:
        import cv2
        import numpy as np

        array = np.array(image.convert("RGB"))
        edges = cv2.Canny(array, 100, 200)
        edges = np.stack([edges] * 3, axis=-1)
        return Image.fromarray(edges)

    def generate(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
    ) -> Image.Image:
        pipeline = self._load()
        control_image = self._canny_edges(image)
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=control_image,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        return result.images[0]
