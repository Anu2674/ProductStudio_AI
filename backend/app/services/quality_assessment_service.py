import io

import cv2
import numpy as np
from PIL import Image

MIN_GOOD_RESOLUTION = 1024


def _to_gray(array):
    return cv2.cvtColor(array, cv2.COLOR_BGR2GRAY)


def _foreground_mask(array):
    gray = _to_gray(array)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return mask


def sharpness_score(array) -> float:
    variance = cv2.Laplacian(_to_gray(array), cv2.CV_64F).var()
    return float(min(variance / 500.0, 1.0) * 100)


def lighting_score(array) -> float:
    mean_brightness = _to_gray(array).mean()
    distance_from_ideal = abs(mean_brightness - 128) / 128
    return float(max(0.0, 1.0 - distance_from_ideal) * 100)


def contrast_score(array) -> float:
    std_dev = _to_gray(array).std()
    return float(min(std_dev / 64.0, 1.0) * 100)


def resolution_score(array) -> float:
    height, width = array.shape[:2]
    smaller_dimension = min(height, width)
    return float(min(smaller_dimension / MIN_GOOD_RESOLUTION, 1.0) * 100)


def background_quality_score(array) -> float:
    height, width = array.shape[:2]
    border = max(1, min(height, width) // 20)
    strips = [
        array[:border, :].reshape(-1, 3),
        array[-border:, :].reshape(-1, 3),
        array[:, :border].reshape(-1, 3),
        array[:, -border:].reshape(-1, 3),
    ]
    border_pixels = np.concatenate(strips)
    variance = border_pixels.astype(np.float32).var()
    return float(max(0.0, 1.0 - min(variance / 2000.0, 1.0)) * 100)


def product_visibility_score(array) -> tuple[float, np.ndarray]:
    mask = _foreground_mask(array)
    foreground_ratio = float(np.count_nonzero(mask)) / mask.size

    if foreground_ratio < 0.15:
        score = foreground_ratio / 0.15
    elif foreground_ratio > 0.9:
        score = max(0.0, 1.0 - (foreground_ratio - 0.9) / 0.1)
    else:
        score = 1.0
    return float(score * 100), mask


def composition_score(array, mask) -> float:
    height, width = array.shape[:2]
    moments = cv2.moments(mask, binaryImage=True)
    if moments["m00"] == 0:
        return 50.0

    centroid_x = moments["m10"] / moments["m00"]
    centroid_y = moments["m01"] / moments["m00"]
    thirds_x = [width / 3, 2 * width / 3]
    thirds_y = [height / 3, 2 * height / 3]
    nearest_x = min(abs(centroid_x - t) for t in thirds_x)
    nearest_y = min(abs(centroid_y - t) for t in thirds_y)
    distance = (nearest_x / width) + (nearest_y / height)
    return float(max(0.0, 1.0 - distance) * 100)


def assess(image_bytes: bytes) -> dict:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    visibility, mask = product_visibility_score(array)
    scores = {
        "sharpness": round(sharpness_score(array), 1),
        "lighting": round(lighting_score(array), 1),
        "contrast": round(contrast_score(array), 1),
        "resolution": round(resolution_score(array), 1),
        "background_quality": round(background_quality_score(array), 1),
        "product_visibility": round(visibility, 1),
        "composition": round(composition_score(array, mask), 1),
    }
    overall = round(sum(scores.values()) / len(scores), 1)

    suggestions = []
    if scores["sharpness"] < 50:
        suggestions.append("Image appears soft or blurry - check focus and camera stability.")
    if scores["lighting"] < 50:
        suggestions.append("Lighting is too dark or too bright - adjust exposure.")
    if scores["contrast"] < 40:
        suggestions.append("Low contrast - the product may look flat.")
    if scores["resolution"] < 50:
        suggestions.append("Resolution is low - use a higher-resolution source image.")
    if scores["background_quality"] < 50:
        suggestions.append("Background is not clean or uniform - consider a plain backdrop.")
    if scores["product_visibility"] < 50:
        suggestions.append("Product is too small or too cropped in the frame.")
    if scores["composition"] < 40:
        suggestions.append("Product placement could better follow the rule of thirds.")

    return {"overall": overall, "scores": scores, "suggestions": suggestions}
