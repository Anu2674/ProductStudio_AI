import io

import cv2
import numpy as np
from PIL import Image


def _pil_to_cv2(image: Image.Image):
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def _cv2_to_pil(array) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(array, cv2.COLOR_BGR2RGB))


def correct_color(array):
    """Gray-world white balance: scales each channel so its mean approaches neutral gray."""
    result = array.astype(np.float32)
    for channel in range(3):
        mean = result[:, :, channel].mean()
        if mean > 0:
            result[:, :, channel] *= 128.0 / mean
    return np.clip(result, 0, 255).astype(np.uint8)


def adjust_lighting_contrast(array):
    """CLAHE on the L channel in LAB space to fix uneven lighting without blowing out color."""
    lab = cv2.cvtColor(array, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    lab = cv2.merge((l_channel, a_channel, b_channel))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def sharpen(array):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return cv2.filter2D(array, -1, kernel)


def enhance(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    array = _pil_to_cv2(image)
    array = correct_color(array)
    array = adjust_lighting_contrast(array)
    array = sharpen(array)

    buffer = io.BytesIO()
    _cv2_to_pil(array).save(buffer, format="PNG")
    return buffer.getvalue()
