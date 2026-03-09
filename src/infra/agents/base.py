from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Generic
from typing import TypeVar

from langgraph.graph import StateGraph
from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName
from pydantic_ai.models import Model

StateT = TypeVar("StateT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[StateT, OutputT]):
    def __init__(self, model: Model | KnownModelName, model_token: str) -> None:
        self._agent: Agent[Any, Any] = self._build_agent(model, model_token)
        self._graph = self._build_graph(self._agent).compile()

    @abstractmethod
    def _build_agent(self, model: Model | KnownModelName, model_token: str) -> Agent[Any, Any]:
        pass

    @abstractmethod
    def _build_graph(self, agent: Agent[Any, Any]) -> StateGraph:
        pass

    @abstractmethod
    def _build_initial_state(self, **kwargs: Any) -> StateT:
        pass

    @abstractmethod
    def _parse_result(self, state: dict[str, Any]) -> OutputT:
        pass

    async def run(self, **kwargs: Any) -> OutputT:
        initial_state = self._build_initial_state(**kwargs)
        async with self._agent:
            final_state = await self._graph.ainvoke(initial_state)  # type: ignore[arg-type]
        return self._parse_result(final_state)
