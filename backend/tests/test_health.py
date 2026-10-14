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
