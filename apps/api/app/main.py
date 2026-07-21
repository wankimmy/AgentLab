from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.router import api_router
from app.core.config import settings
from app.observability.logging import RequestContextMiddleware, configure_logging
from app.observability.metrics import metrics_payload
from app.observability.middleware import DemoReadOnlyMiddleware, MetricsMiddleware
from app.observability.otel import instrument_fastapi, setup_otel

configure_logging()
setup_otel()
app = FastAPI(title="AgentLab API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(DemoReadOnlyMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestContextMiddleware)

app.include_router(api_router, prefix="/api/v1")

instrument_fastapi(app)


@app.get("/metrics")
def prometheus_metrics() -> Response:
    payload, content_type = metrics_payload()
    return Response(content=payload, media_type=content_type)
