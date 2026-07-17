import io

from PIL import Image


def _sample_png_bytes():
    image = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_segment_returns_transparent_png(client):
    response = client.post("/segment", files={"file": ("product.png", _sample_png_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(response.content)).mode == "RGBA"
