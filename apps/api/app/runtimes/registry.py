from app.models.entities import RuntimeType
from app.runtimes.langgraph_adapter import LangGraphRuntimeAdapter
from app.runtimes.native_adapter import NativeRuntimeAdapter
from app.runtimes.protocol import RuntimeAdapter

_native = NativeRuntimeAdapter()
_langgraph = LangGraphRuntimeAdapter()


def get_runtime_adapter(runtime_type: RuntimeType) -> RuntimeAdapter:
    if runtime_type == RuntimeType.langgraph:
        return _langgraph
    return _native
