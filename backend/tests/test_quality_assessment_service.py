import io

from PIL import Image

from app.services.quality_assessment_service import assess


def _sample_png_bytes(color=(180, 180, 180), size=(128, 128)):
    image = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_assess_returns_all_expected_dimensions():
    result = assess(_sample_png_bytes())

    assert set(result["scores"].keys()) == {
        "sharpness",
        "lighting",
        "contrast",
        "resolution",
        "background_quality",
        "product_visibility",
        "composition",
    }
    assert 0 <= result["overall"] <= 100
    assert isinstance(result["suggestions"], list)


def test_assess_flags_low_resolution_image():
    result = assess(_sample_png_bytes(size=(20, 20)))
    assert result["scores"]["resolution"] < 50
    assert any("resolution" in suggestion.lower() for suggestion in result["suggestions"])
