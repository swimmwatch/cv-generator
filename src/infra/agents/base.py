from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Generic
from typing import TypeVar

import httpx
import logfire
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph
from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName
from pydantic_ai.models import Model

StateT = TypeVar("StateT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[StateT, OutputT]):
    def __init__(
        self,
        model: Model | KnownModelName,
        model_token: str,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._agent: Agent[Any, Any] = self._build_agent(model, model_token)
        self._graph = self._build_graph(self._agent).compile(checkpointer=checkpointer)

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

    @abstractmethod
    def _build_error_result(self) -> OutputT:
        pass

    async def run(self, thread_id: str | None = None, **kwargs: Any) -> OutputT:
        config = {"configurable": {"thread_id": thread_id}} if thread_id else None
        initial_state = self._build_initial_state(**kwargs)
        try:
            async with self._agent:
                final_state = await self._graph.ainvoke(initial_state, config=config)  # type: ignore[arg-type]
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logfire.error("{agent}.run connection failed", agent=type(self).__name__, error=str(exc))
            return self._build_error_result()
        return self._parse_result(final_state)
