from sqlalchemy.orm import Session

from app.models.entities import AgentVersion, Tool, ToolMode

ALLOWED_TOOL_NAMES = frozenset({"calculator", "knowledge_search", "current_datetime"})

DEFAULT_LIMITS = {
    "max_agent_steps": 5,
    "max_tool_calls": 3,
    "timeout_seconds": 60,
}


def get_runtime_limits(tool_config: dict) -> dict[str, int]:
    limits = tool_config.get("limits") or {}
    return {
        "max_agent_steps": int(limits.get("max_agent_steps", DEFAULT_LIMITS["max_agent_steps"])),
        "max_tool_calls": int(limits.get("max_tool_calls", DEFAULT_LIMITS["max_tool_calls"])),
        "timeout_seconds": int(limits.get("timeout_seconds", DEFAULT_LIMITS["timeout_seconds"])),
    }


def get_tool_mode(tool_config: dict, tool_name: str) -> ToolMode:
    raw = tool_config.get(tool_name, "disabled")
    if isinstance(raw, dict):
        raw = raw.get("mode", "disabled")
    try:
        return ToolMode(str(raw))
    except ValueError:
        return ToolMode.disabled


def has_enabled_tools(version: AgentVersion) -> bool:
    config = version.tool_config or {}
    for name in ALLOWED_TOOL_NAMES:
        if get_tool_mode(config, name) != ToolMode.disabled:
            return True
    return False


def build_tool_schemas(db: Session, version: AgentVersion) -> list[dict]:
    config = version.tool_config or {}
    tools = db.query(Tool).filter(Tool.name.in_(ALLOWED_TOOL_NAMES)).all()
    by_name = {t.name: t for t in tools}
    schemas: list[dict] = []
    for name in ALLOWED_TOOL_NAMES:
        if get_tool_mode(config, name) == ToolMode.disabled:
            continue
        tool = by_name.get(name)
        if not tool:
            continue
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
        )
    return schemas
