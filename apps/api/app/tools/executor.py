import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AgentVersion, AuditLog, Conversation, ToolMode
from app.tools.calculator import CalculatorError, evaluate_expression
from app.tools.current_datetime import get_current_datetime
from app.tools.knowledge_search import search_knowledge
from app.tools.registry import ALLOWED_TOOL_NAMES, get_tool_mode


@dataclass
class ToolContext:
    db: Session
    version: AgentVersion
    conversation: Conversation
    trace_id: uuid.UUID
    user_id: uuid.UUID


class ToolExecutionError(Exception):
    def __init__(self, message: str, code: str = "tool_error") -> None:
        super().__init__(message)
        self.code = code


def _write_audit(
    ctx: ToolContext,
    tool_name: str,
    arguments: dict,
    status: str,
    duration_ms: int,
    result: Any = None,
    error: str | None = None,
) -> None:
    ctx.db.add(
        AuditLog(
            user_id=ctx.user_id,
            action="tool.execute",
            resource_type="tool",
            resource_id=tool_name,
            trace_id=ctx.trace_id,
            details={
                "arguments": arguments,
                "status": status,
                "duration_ms": duration_ms,
                "result": result,
                "error": error,
            },
        )
    )


def execute_tool(
    ctx: ToolContext,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    if tool_name not in ALLOWED_TOOL_NAMES:
        raise ToolExecutionError("Tool not permitted", "permission_denied")

    mode = get_tool_mode(ctx.version.tool_config or {}, tool_name)
    if mode == ToolMode.disabled:
        raise ToolExecutionError("Tool disabled", "tool_disabled")

    start = time.perf_counter()
    output: dict[str, Any]
    try:
        if tool_name == "calculator":
            expression = str(arguments.get("expression", ""))
            result = evaluate_expression(expression)
            output = {"result": result, "expression": expression}
        elif tool_name == "knowledge_search":
            query = str(arguments.get("query", ""))
            collection_id = arguments.get("collection_id")
            output = search_knowledge(
                ctx.db,
                ctx.version,
                query,
                str(collection_id) if collection_id else None,
            )
        elif tool_name == "current_datetime":
            tz = str(arguments.get("timezone", "UTC"))
            output = get_current_datetime(tz)
        else:
            raise ToolExecutionError("Tool not implemented", "not_implemented")
    except (CalculatorError, ValueError) as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        _write_audit(ctx, tool_name, arguments, "error", duration_ms, error=str(exc))
        raise ToolExecutionError(str(exc), "validation_error") from exc

    duration_ms = int((time.perf_counter() - start) * 1000)
    _write_audit(ctx, tool_name, arguments, "success", duration_ms, result=output)
    return output


def tool_result_content(result: dict[str, Any]) -> str:
    return json.dumps(result)
