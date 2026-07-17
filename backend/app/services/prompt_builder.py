SCENE_TEMPLATES = {
    "studio_white": "professional product photograph on a seamless white studio background",
    "lifestyle": "lifestyle product photograph in a naturally lit lifestyle setting",
    "indoor": "product photograph staged in a modern indoor environment",
    "outdoor": "product photograph staged in a natural outdoor environment",
    "marketplace": "clean marketplace-ready product photograph with a neutral background",
}

LIGHTING_TEMPLATES = {
    "soft": "soft diffused lighting",
    "natural": "natural daylight lighting",
    "dramatic": "dramatic studio lighting with strong contrast",
}

CAMERA_ANGLE_TEMPLATES = {
    "front": "front-facing eye-level shot",
    "three_quarter": "three-quarter angle shot",
    "top_down": "top-down flat lay shot",
}

DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, watermark, text, extra objects"


def build_prompt(scene_type: str, lighting: str, camera_angle: str) -> tuple[str, str]:
    scene = SCENE_TEMPLATES.get(scene_type, SCENE_TEMPLATES["studio_white"])
    light = LIGHTING_TEMPLATES.get(lighting, LIGHTING_TEMPLATES["soft"])
    angle = CAMERA_ANGLE_TEMPLATES.get(camera_angle, CAMERA_ANGLE_TEMPLATES["front"])
    prompt = f"{scene}, {light}, {angle}, high detail, professional photography"
    return prompt, DEFAULT_NEGATIVE_PROMPT
