from http import HTTPStatus
from typing import Any
from typing import Literal

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
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from core import domains
from infra.agents.base import BaseAgent
from infra.agents.schemas.job import AgentState
from infra.agents.schemas.job import JobCard
from infra.agents.schemas.job import JobParserError
from infra.agents.schemas.job import JobParserResult
from infra.logger.utils import get_logger

logger = get_logger(__name__)


_FETCH_INSTRUCTIONS = """\
Navigate to the provided URL using the browser. \
If a cookie or consent banner blocks content, dismiss it. \
Return the full visible text content of the page without summarization.\
"""

_EXTRACT_INSTRUCTIONS = """\
Extract structured job posting information from the provided text.
Normalize technology names (e.g. 'Postgres' -> 'PostgreSQL', 'JS' -> 'JavaScript').
Separate mandatory requirements from nice-to-have ones.
Remove HTML artifacts, navigation elements, and irrelevant content from the text field.
Detect the language and set language_code accordingly.
Generate a 1-3 sentence summary.
Populate the text field with the cleaned job description.
Set is_job_posting to false if the content is not a job posting.\
"""

_FETCH_PROMPT = "Open this page and return its full text content:\n{job_reference}"

_EXTRACT_PROMPT = "Parse the following page content into a structured job card:\n\n{page_content}"


ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]


class JobParserAgent(BaseAgent[AgentState, JobParserResult]):
    def __init__(
        self,
        model_name: str,
        model_token: str,
        mcp_proxy_url: str,
        mcp_headers: dict[str, str],
        max_retries: int = 3,
        max_tokens: int = 16384,
        timeout: float = 60.0,
        reasoning_effort: ReasoningEffort = "low",
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._mcp_proxy_url = mcp_proxy_url
        self._max_retries = max_retries
        self._mcp_headers = mcp_headers
        self._model_settings = OpenAIChatModelSettings(
            max_tokens=max_tokens,
            timeout=timeout,
            openai_reasoning_effort=reasoning_effort,
        )
        model = OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(api_key=model_token),
        )
        self._extract_agent: Agent[Any, JobCard] = Agent(
            model,
            output_type=JobCard,
            instructions=_EXTRACT_INSTRUCTIONS,
            model_settings=self._model_settings,
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
            output_type=str,
            toolsets=[playwright],
            instructions=_FETCH_INSTRUCTIONS,
            model_settings=self._model_settings,
        )

    def _build_graph(self, agent: Agent[Any, Any]) -> StateGraph:
        fetch_agent = agent
        extract_agent = self._extract_agent
        max_retries = self._max_retries

        async def fetch_page(state: AgentState) -> dict:
            retry = state["retries"]
            with logfire.span(
                "job_parser.fetch_page attempt={attempt}",
                attempt=retry + 1,
                job_reference=state["job_reference"][:200],
            ):
                try:
                    run_result = await fetch_agent.run(
                        _FETCH_PROMPT.format(job_reference=state["job_reference"]),
                    )
                    return {"page_content": run_result.output, "error": None}
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    logfire.error("job_parser.fetch_page connection failed", error=str(exc))
                    return {"error": str(exc), "retries": max_retries}
                except ModelHTTPError as exc:
                    if exc.status_code == HTTPStatus.TOO_MANY_REQUESTS and retry < max_retries:
                        logfire.warn("job_parser.fetch_page rate limited", error=str(exc))
                        return {"error": str(exc), "retries": retry + 1}
                    logfire.error("job_parser.fetch_page model HTTP error", error=str(exc))
                    return {"error": str(exc), "retries": max_retries}
                except Exception as exc:
                    if retry < max_retries:
                        logfire.warn("job_parser.fetch_page failed, will retry", error=str(exc))
                        return {"error": str(exc), "retries": retry + 1}
                    logfire.error("job_parser.fetch_page exhausted retries", error=str(exc))
                    return {"error": str(exc), "retries": max_retries}

        async def extract(state: AgentState) -> dict:
            retry = state["retries"]
            with logfire.span("job_parser.extract attempt={attempt}", attempt=retry + 1):
                try:
                    run_result = await extract_agent.run(
                        _EXTRACT_PROMPT.format(page_content=state["page_content"]),
                    )
                    logfire.info("job_parser.extract succeeded", job_title=run_result.output.job_title)
                    return {"parsed_result": run_result.output, "error": None}
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    logfire.error("job_parser.extract connection failed", error=str(exc))
                    return {"error": str(exc), "retries": max_retries}
                except ModelHTTPError as exc:
                    if exc.status_code == HTTPStatus.TOO_MANY_REQUESTS and retry < max_retries:
                        return {"error": str(exc), "retries": retry + 1}
                    return {"error": str(exc), "retries": max_retries}
                except Exception as exc:
                    if retry < max_retries:
                        logfire.warn("job_parser.extract failed, will retry", error=str(exc))
                        return {"error": str(exc), "retries": retry + 1}
                    logfire.error("job_parser.extract exhausted retries", error=str(exc))
                    return {"error": str(exc), "retries": max_retries}

        async def validate(state: AgentState) -> dict:
            job_card = state["parsed_result"]
            if job_card is None:
                return {"error": "No parsed result to validate"}
            if not job_card.is_job_posting:
                logfire.warn("job_parser.validate: not a job posting")
                return {"parsed_result": None, "error": JobParserError.NOT_A_JOB_POSTING}
            if not job_card.job_title and not job_card.requirements:
                logfire.warn("job_parser.validate: missing required fields")
                return {"parsed_result": None, "error": JobParserError.MISSING_REQUIRED_FIELDS}
            logfire.info("job_parser.validate: valid", job_title=job_card.job_title)
            return {"error": None}

        def route_after_fetch(state: AgentState) -> str:
            if state.get("page_content") and not state.get("error"):
                return "extract"
            if state["retries"] < max_retries:
                return "fetch_page"
            return END

        def route_after_extract(state: AgentState) -> str:
            if state.get("parsed_result") and not state.get("error"):
                return "validate"
            if state["retries"] < max_retries:
                return "extract"
            return END

        graph = StateGraph(AgentState)
        graph.add_node("fetch_page", fetch_page)
        graph.add_node("extract", extract)
        graph.add_node("validate", validate)
        graph.add_edge(START, "fetch_page")
        graph.add_conditional_edges("fetch_page", route_after_fetch)
        graph.add_conditional_edges("extract", route_after_extract)
        graph.add_edge("validate", END)

        return graph

    def _build_initial_state(self, **kwargs: Any) -> AgentState:
        return {
            "job_reference": kwargs["job_reference"],
            "page_content": None,
            "parsed_result": None,
            "error": None,
            "retries": 0,
        }

    def _parse_result(self, state: dict[str, Any]) -> JobParserResult:
        if state.get("parsed_result"):
            return JobParserResult(success=True, result=state["parsed_result"])
        return self._build_error_result(error=state.get("error"))

    def _build_error_result(self, error: str | None = None) -> JobParserResult:
        return JobParserResult(success=False, result=None, error=error)

    @staticmethod
    def chunk(
        job_id: str,
        user_id: str,
        job_card: JobCard,
    ) -> list[domains.JobChunk]:
        base_metadata = {
            "job_id": job_id,
            "user_id": user_id,
        }
        chunks: list[domains.JobChunk] = []

        if job_card.text:
            chunks.append(
                domains.JobChunk(
                    job_id=job_id,
                    user_id=user_id,
                    section="full_job",
                    content=job_card.text,
                    metadata=base_metadata,
                )
            )

        if job_card.summary:
            chunks.append(
                domains.JobChunk(
                    job_id=job_id,
                    user_id=user_id,
                    section="summary",
                    content=job_card.summary,
                    metadata={**base_metadata, "section": "summary"},
                )
            )

        if job_card.required_skills:
            chunks.append(
                domains.JobChunk(
                    job_id=job_id,
                    user_id=user_id,
                    section="required_skills",
                    content=", ".join(job_card.required_skills),
                    metadata={**base_metadata, "section": "required_skills"},
                )
            )

        if job_card.nice_to_have_skills:
            chunks.append(
                domains.JobChunk(
                    job_id=job_id,
                    user_id=user_id,
                    section="nice_to_have_skills",
                    content=", ".join(job_card.nice_to_have_skills),
                    metadata={**base_metadata, "section": "nice_to_have_skills"},
                )
            )

        if job_card.responsibilities:
            chunks.append(
                domains.JobChunk(
                    job_id=job_id,
                    user_id=user_id,
                    section="responsibilities",
                    content="\n".join(job_card.responsibilities),
                    metadata={**base_metadata, "section": "responsibilities"},
                )
            )

        if job_card.requirements:
            chunks.append(
                domains.JobChunk(
                    job_id=job_id,
                    user_id=user_id,
                    section="requirements",
                    content="\n".join(job_card.requirements),
                    metadata={**base_metadata, "section": "requirements"},
                )
            )

        if job_card.conditions:
            chunks.append(
                domains.JobChunk(
                    job_id=job_id,
                    user_id=user_id,
                    section="conditions",
                    content="\n".join(job_card.conditions),
                    metadata={**base_metadata, "section": "conditions"},
                )
            )

        return chunks
