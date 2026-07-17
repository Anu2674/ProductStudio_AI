import numpy as np
from PIL import Image


class SAM2Pipeline:
    """Wraps Meta's SAM2 model for automatic product segmentation and background removal.

    Model weights are loaded lazily on first use so importing this module (and the
    FastAPI app around it) never requires torch/sam2 to be installed or a GPU to be
    present - only actually calling remove_background() does.
    """

    def __init__(self, checkpoint_path: str, model_cfg: str, device: str = "cuda"):
        self.checkpoint_path = checkpoint_path
        self.model_cfg = model_cfg
        self.device = device
        self._predictor = None

    def _load(self):
        if self._predictor is None:
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            sam2_model = build_sam2(self.model_cfg, self.checkpoint_path, device=self.device)
            self._predictor = SAM2ImagePredictor(sam2_model)
        return self._predictor

    def remove_background(self, image: Image.Image) -> Image.Image:
        predictor = self._load()
        image_rgb = np.array(image.convert("RGB"))
        predictor.set_image(image_rgb)

        height, width = image_rgb.shape[:2]
        center_point = np.array([[width // 2, height // 2]])
        point_labels = np.array([1])

        masks, scores, _ = predictor.predict(
            point_coords=center_point,
            point_labels=point_labels,
            multimask_output=True,
        )
        best_mask = masks[int(np.argmax(scores))]

        rgba = image.convert("RGBA")
        alpha = (best_mask * 255).astype(np.uint8)
        r, g, b, _ = rgba.split()
        return Image.merge("RGBA", (r, g, b, Image.fromarray(alpha)))
