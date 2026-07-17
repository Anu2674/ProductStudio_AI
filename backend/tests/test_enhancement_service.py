import io

from PIL import Image

from app.services.enhancement_service import enhance


def _sample_png_bytes():
    image = Image.new("RGB", (64, 64), color=(60, 90, 120))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_enhance_returns_valid_png_of_same_dimensions():
    original_bytes = _sample_png_bytes()
    result_bytes = enhance(original_bytes)

    result_image = Image.open(io.BytesIO(result_bytes))
    assert result_image.format == "PNG"
    assert result_image.size == (64, 64)
