from PIL import Image, ImageFilter, ImageEnhance
import logging
import numpy as np

logger = logging.getLogger(__name__)


class SAM2Pipeline:
    """PLACEHOLDER background removal using PIL image processing.

    Not a model. Kept only so the service and tests boot without a GPU when
    PIPELINE_MODE=mock. The real implementation is sam2_pipeline.SAM2Pipeline.
    """

    requires_mask = False

    def __init__(self, checkpoint_path=None, model_config=None, device="cpu", **_):
        self.device = device

    def segment(self, image: Image.Image) -> np.ndarray:
        """Rough boolean mask (True = non-light pixels). Brightness threshold only."""
        img_array = np.array(image.convert("RGB"))
        brightness = np.mean(img_array, axis=2)
        return brightness <= 200

    def remove_background(self, image: Image.Image) -> Image.Image:
        """Remove background by detecting and enhancing subject"""
        img_array = np.array(image.convert("RGB"))

        # Detect light background
        brightness = np.mean(img_array, axis=2)
        light_mask = brightness > 200

        # Enhance subject contrast
        result_array = img_array.copy()
        result_array[~light_mask] = np.clip(result_array[~light_mask] * 1.2, 0, 255).astype(np.uint8)

        result = Image.fromarray(result_array.astype('uint8'))
        return result.filter(ImageFilter.SMOOTH_MORE)


class SDXLControlNetPipeline:
    """PLACEHOLDER photo generation: brightness-keyed color fill + global tone tweak.

    Not a model. Real implementation is
    sdxl_inpaint_pipeline.SDXLInpaintControlNetPipeline.
    """

    requires_mask = False

    def __init__(self, base_model_id=None, controlnet_model_id=None, device="cpu", **_):
        self.device = device
        self.color_map = {
            "yellow": (255, 250, 100),
            "blue": (100, 150, 255),
            "green": (120, 200, 120),
            "red": (255, 100, 100),
            "pink": (255, 150, 200),
            "purple": (200, 100, 255),
            "orange": (255, 165, 80),
            "gray": (200, 200, 200),
            "grey": (200, 200, 200),
            "black": (40, 40, 40),
            "white": (245, 245, 245),
        }

    def generate(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        product_mask=None,
        **_,
    ) -> Image.Image:
        """Generate styled product photo with background transformation"""
        return self._transform_product_photo(image, prompt)

    def _transform_product_photo(self, image: Image.Image, prompt: str) -> Image.Image:
        """Transform product photo based on prompt"""
        prompt_lower = prompt.lower()

        # Check for color request
        target_color = None
        for color_name, rgb in self.color_map.items():
            if color_name in prompt_lower:
                target_color = rgb
                break

        result = image.copy()

        # If color specified, change background
        if target_color:
            result = self._apply_background_color(result, target_color)

        # Apply lighting/style based on prompt
        result = self._apply_lighting_effects(result, prompt_lower)

        return result

    def _apply_background_color(self, image: Image.Image, color: tuple) -> Image.Image:
        """Replace light background with target color"""
        img_array = np.array(image.convert("RGB"))

        # Detect light pixels (background)
        brightness = np.mean(img_array, axis=2)
        light_mask = brightness > 180

        # Apply color to background
        result = img_array.copy()
        result[light_mask] = color

        # Smooth edges
        result = self._smooth_edges(result, light_mask)

        return Image.fromarray(result.astype('uint8'))

    def _smooth_edges(self, img_array: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Smooth edges between subject and background"""
        try:
            from scipy import ndimage
            # Dilate and blur for smooth transition
            dilated = ndimage.binary_dilation(mask, iterations=2)
            blurred_mask = ndimage.gaussian_filter(dilated.astype(float), sigma=3)

            # Blend edges
            for i in range(3):
                img_array[:,:,i] = (img_array[:,:,i] * (1 - blurred_mask*0.1)).astype(np.uint8)

            return img_array
        except:
            return img_array

    def _apply_lighting_effects(self, image: Image.Image, prompt_lower: str) -> Image.Image:
        """Apply lighting and style effects"""
        if any(word in prompt_lower for word in ["bright", "studio", "professional", "clean"]):
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.25)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)

        elif any(word in prompt_lower for word in ["dark", "moody", "dramatic"]):
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(0.75)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)

        elif any(word in prompt_lower for word in ["warm", "sunset", "golden"]):
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.2)

        return image.filter(ImageFilter.SMOOTH)
