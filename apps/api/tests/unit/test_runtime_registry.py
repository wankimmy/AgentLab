from app.models.entities import RuntimeType
from app.runtimes.langgraph_adapter import LangGraphRuntimeAdapter
from app.runtimes.native_adapter import NativeRuntimeAdapter
from app.runtimes.registry import get_runtime_adapter


def test_registry_native():
    adapter = get_runtime_adapter(RuntimeType.native)
    assert isinstance(adapter, NativeRuntimeAdapter)


def test_registry_langgraph():
    adapter = get_runtime_adapter(RuntimeType.langgraph)
    assert isinstance(adapter, LangGraphRuntimeAdapter)
