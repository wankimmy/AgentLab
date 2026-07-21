"""LangGraph runtime adapter — thin graph over shared turn helpers."""

import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.models.entities import AgentVersion, Conversation
from app.services.turn_models import StreamResult, TurnOverrides
from app.services.native_runtime import resolve_user_id, stream_native_turn
from app.runtimes.simple_turn import stream_simple_turn
from app.tools.registry import has_enabled_tools

logger = logging.getLogger(__name__)


class TurnGraphState(TypedDict, total=False):
    prepared: bool
    runtime_label: str


def _build_prepare_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "LangGraph runtime selected but langgraph package is not installed"
        ) from exc

    def assemble_node(state: TurnGraphState) -> dict[str, Any]:
        return {"prepared": True, "runtime_label": state.get("runtime_label", "langgraph")}

    graph = StateGraph(TurnGraphState)
    graph.add_node("assemble", assemble_node)
    graph.add_edge(START, "assemble")
    graph.add_edge("assemble", END)
    return graph.compile()


class LangGraphRuntimeAdapter:
    async def stream_turn(
        self,
        db: Session,
        conversation: Conversation,
        version: AgentVersion,
        user_content: str,
        overrides: TurnOverrides | None,
        user_id: uuid.UUID,
    ) -> AsyncIterator[StreamResult]:
        graph = _build_prepare_graph()
        graph.invoke({"runtime_label": version.runtime_type.value, "prepared": False})
        logger.debug("LangGraph prepare graph completed for version %s", version.id)

        if has_enabled_tools(version):
            async for result in stream_native_turn(
                db, conversation, version, user_content, overrides, user_id
            ):
                yield result
            return
        async for result in stream_simple_turn(
            db, conversation, version, user_content, overrides
        ):
            yield result
