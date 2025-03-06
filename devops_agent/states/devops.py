from enum import Enum
from typing import List, TypedDict

from langgraph.graph import MessagesState


class Log(TypedDict):
    """A state that represents a log of an action performed by the agent."""

    message: str
    command: List
    done: bool
    result: str


class Suggestions(TypedDict):
    """A state that represents suggestions by the agent."""

    id: str
    name: str


class AgentState(MessagesState):
    """A state that is the main agent state which is a subclass of the `MessagesState` class from langgraph."""

    class AutoApprove(Enum):
        YES = "yes"
        NO = "no"

    auto_approve: AutoApprove = AutoApprove.NO.value
    model: str
    summary: str
    logs: List[Log]
    devopsSuggestions: List[Suggestions]
