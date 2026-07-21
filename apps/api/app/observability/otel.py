"""OpenTelemetry setup and runtime span helpers."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.core.config import settings

_tracer = None
_initialized = False


def setup_otel() -> None:
    global _tracer, _initialized
    if _initialized:
        return
    _initialized = True

    if not settings.otel_enabled or settings.app_env == "test":
        return

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    elif settings.app_env != "test":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("agentlab")


def instrument_fastapi(app: Any) -> None:
    if not settings.otel_enabled or settings.app_env == "test":
        return
    setup_otel()
    from opentelemetry.instrumentation import fastapi as otel_fastapi
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    _original_get_route_details = otel_fastapi._get_route_details

    def _safe_get_route_details(scope: dict) -> str:
        route = scope.get("route")
        if route is not None and hasattr(route, "path"):
            return route.path
        try:
            return _original_get_route_details(scope)
        except AttributeError:
            return scope.get("path") or "unknown"

    otel_fastapi._get_route_details = _safe_get_route_details
    FastAPIInstrumentor.instrument_app(app)


def _get_tracer():
    if not settings.otel_enabled or settings.app_env == "test":
        return None
    setup_otel()
    if _tracer is not None:
        return _tracer
    from opentelemetry import trace

    return trace.get_tracer("agentlab")


@contextmanager
def span_agent_turn(
    *,
    agent_version_id: str,
    model: str,
    runtime: str,
) -> Iterator[None]:
    tracer = _get_tracer()
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(
        "agent.turn",
        attributes={
            "agent_version_id": agent_version_id,
            "model": model,
            "runtime": runtime,
        },
    ):
        yield


@contextmanager
def span_provider_chat(*, provider: str, model: str) -> Iterator[None]:
    tracer = _get_tracer()
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(
        "provider.chat",
        attributes={"provider": provider, "model": model},
    ):
        yield


@contextmanager
def span_retrieval_search(*, version_id: str, top_k: int, mode: str) -> Iterator[None]:
    tracer = _get_tracer()
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(
        "retrieval.search",
        attributes={"agent_version_id": version_id, "top_k": top_k, "mode": mode},
    ):
        yield


@contextmanager
def span_tool_execute(*, tool_name: str) -> Iterator[None]:
    tracer = _get_tracer()
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(
        "tool.execute",
        attributes={"tool_name": tool_name},
    ):
        yield
