import base64

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chat import ChatRequest


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "online"}


def test_chat_request_accepts_model_selection() -> None:
    request = ChatRequest(
        model="qwen2.5:3b",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert request.model == "qwen2.5:3b"


def test_chat_request_accepts_web_search() -> None:
    request = ChatRequest(
        messages=[{"role": "user", "content": "What changed today?"}],
        web_search=True,
    )

    assert request.web_search is True


def test_chat_request_accepts_image_attachment() -> None:
    request = ChatRequest(
        messages=[
            {
                "role": "user",
                "content": "Describe this image.",
                "images": [
                    {
                        "name": "pixel.png",
                        "media_type": "image/png",
                        "data": base64.b64encode(b"small image").decode(),
                    }
                ],
            }
        ],
    )

    assert request.messages[0].images[0].name == "pixel.png"
