from app.core.config import settings
from app.observability import otel


def test_otel_setup_noop_in_test_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "test")
    otel._initialized = False
    otel._tracer = None
    otel.setup_otel()
    assert otel._tracer is None
