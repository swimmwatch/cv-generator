from http import HTTPStatus
from typing import Any

import httpx
import logfire
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models import KnownModelName
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from infra.agents.base import BaseAgent
from infra.agents.schemas.job import AgentState
from infra.agents.schemas.job import JobCard
from infra.agents.schemas.job import JobParserResult

_INSTRUCTIONS = """\
You are a job posting parser.
If the input is a URL, use playwright to fetch the page content.

IMPORTANT: browser_navigate already returns a page snapshot. \
Do NOT call browser_snapshot after a successful navigation. \
Only use browser_snapshot after clicking an element or waiting for dynamic content.

URL handling:
1. Open the page with browser_navigate.
2. If navigation fails (timeout, net::ERR_ABORTED, net::ERR_TIMED_OUT, redirect), \
retry the URL once. If it still fails, use browser_snapshot to get whatever loaded.
3. If a cookie banner or login wall blocks content, dismiss it with browser_click, \
then call browser_snapshot to get the updated page.

Extraction rules:
- Normalize technology names (e.g. 'Postgres' -> 'PostgreSQL', 'JS' -> 'JavaScript').
- Separate mandatory requirements from nice-to-have ones.
- Remove HTML artifacts, navigation, sidebars, and irrelevant site content.
- Detect the language and set language_code accordingly.
- If a field is not present, omit it or leave it empty.
- Generate a 1-3 sentence summary.
- Populate 'text' with the full job description, \
cleaned of navigation, ads, banners, headers, footers, and sidebars.\
"""


class JobParserAgent(BaseAgent[AgentState, JobParserResult]):
    def __init__(
        self,
        model_name: str,
        model_token: str,
        mcp_proxy_url: str,
        mcp_headers: dict[str, str],
        max_retries: int = 3,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._mcp_proxy_url = mcp_proxy_url
        self._max_retries = max_retries
        self._mcp_headers = mcp_headers
        model = OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(api_key=model_token),
        )
        super().__init__(model, model_token, checkpointer=checkpointer)

    def _build_agent(self, model: Model | KnownModelName, model_token: str) -> Agent[Any, Any]:
        playwright = MCPServerStreamableHTTP(
            f"{self._mcp_proxy_url}/playwright/mcp",
            tool_prefix="playwright",
            headers=self._mcp_headers,
        )

        return Agent(
            model,
            output_type=JobCard,
            toolsets=[playwright],
            instructions=_INSTRUCTIONS,
        )

    def _build_graph(self, agent: Agent[Any, Any]) -> StateGraph:
        async def parse(state: AgentState) -> dict:
            retry = state["retries"]
            with logfire.span(
                "job_parser.parse attempt={attempt}",
                attempt=retry + 1,
                job_reference=state["job_reference"][:200],
            ):
                try:
                    run_result = await agent.run(
                        f"Parse this job posting and extract structured information:\n\n{state['job_reference']}",
                    )
                    job_card = run_result.output
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    logfire.error("job_parser.parse MCP connection failed", error=str(exc))
                    return {
                        "parsed_result": None,
                        "error": f"MCP server connection failed: {exc}",
                        "retries": self._max_retries,
                    }
                except ModelHTTPError as exc:
                    if exc.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                        logfire.warn("job_parser.parse rate limited", error=str(exc))
                        if retry < self._max_retries:
                            return {"retries": retry + 1, "parsed_result": None, "error": str(exc)}
                    logfire.error(
                        "job_parser.parse model HTTP error",
                        status_code=exc.status_code,
                        error=str(exc),
                    )
                    return {
                        "parsed_result": None,
                        "error": f"Model API error (HTTP {exc.status_code}): {exc}",
                        "retries": self._max_retries,
                    }
                except Exception as exc:
                    if retry < self._max_retries:
                        logfire.warn(
                            "job_parser.parse failed, scheduling retry {next_attempt}",
                            next_attempt=retry + 2,
                            error=str(exc),
                        )
                        return {"retries": retry + 1, "parsed_result": None, "error": str(exc)}
                    logfire.error("job_parser.parse exhausted retries", error=str(exc))
                    return {
                        "parsed_result": None,
                        "error": f"Failed after {self._max_retries} retries: {exc}",
                        "retries": self._max_retries,
                    }

                if not job_card.job_title and not job_card.requirements:
                    logfire.warn("job_parser.parse result missing required fields")
                    return {
                        "parsed_result": None,
                        "error": "Parsed result missing required fields (job_title or requirements)",
                        "retries": self._max_retries,
                    }

                logfire.info(
                    "job_parser.parse succeeded",
                    job_title=job_card.job_title,
                )
                return {"parsed_result": job_card, "error": None}

        def should_retry(state: AgentState) -> str:
            if state.get("error") and not state.get("parsed_result") and state["retries"] < self._max_retries:
                return "parse"
            return END

        graph = StateGraph(AgentState)
        graph.add_node("parse", parse)
        graph.add_edge(START, "parse")
        graph.add_conditional_edges("parse", should_retry, {"parse": "parse", END: END})

        return graph

    def _build_initial_state(self, **kwargs: Any) -> AgentState:
        return {
            "job_reference": kwargs["job_reference"],
            "parsed_result": None,
            "error": None,
            "retries": 0,
        }

    def _parse_result(self, state: dict[str, Any]) -> JobParserResult:
        if state.get("parsed_result"):
            return JobParserResult(success=True, result=state["parsed_result"])
        return self._build_error_result()

    def _build_error_result(self) -> JobParserResult:
        return JobParserResult(success=False, result=None)
