from fastapi.testclient import TestClient

from app.main import app


def test_metrics_endpoint_returns_prometheus_text():
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_request_id_header_on_api():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")
