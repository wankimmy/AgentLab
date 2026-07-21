import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_health_responds_quickly():
    client = TestClient(app)
    start = time.perf_counter()
    response = client.get("/api/v1/health")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 2.0
