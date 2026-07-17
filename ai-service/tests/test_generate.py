import io

from PIL import Image


def _sample_png_bytes():
    image = Image.new("RGB", (10, 10), color=(0, 255, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_generate_returns_png(client):
    response = client.post(
        "/generate",
        files={"file": ("product.png", _sample_png_bytes(), "image/png")},
        data={"prompt": "studio shot", "negative_prompt": "blurry"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_generate_defaults_negative_prompt_to_empty(client):
    response = client.post(
        "/generate",
        files={"file": ("product.png", _sample_png_bytes(), "image/png")},
        data={"prompt": "studio shot"},
    )
    assert response.status_code == 200
