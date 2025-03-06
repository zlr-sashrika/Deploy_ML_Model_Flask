import uuid
from typing import Any, Optional

from langchain_core.callbacks.base import BaseCallbackManager, Callbacks
from langchain_core.runnables import RunnableConfig


class CustomNodeConfig(RunnableConfig):
    """A config class that inherits langchain's `RunnableConfig` class to extend it's configuration abilities."""

    node_name: str = "Tool"
    tags: list[str] = ["{} calling LLM."]
    metadata: dict[str, Any]
    callbacks: Callbacks
    run_name: str
    max_concurrency: Optional[int]
    recursion_limit: int = 1
    configurable: dict[str, Any]
    run_id: Optional[uuid.UUID]
