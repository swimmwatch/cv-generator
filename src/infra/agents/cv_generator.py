from http import HTTPStatus
from json import dumps
from typing import Any

import httpx
import logfire
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models import KnownModelName
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from core import dal
from infra.agents.base import BaseAgent
from infra.agents.schemas.cv_generator import CvGeneratorResult
from infra.agents.schemas.cv_generator import CvGeneratorState
from infra.agents.schemas.cv_generator import EvidenceMap
from infra.agents.schemas.cv_generator import VacancyAnalysis
from infra.agents.schemas.resume import ResumePayload
from infra.agents.tools.search import SearchDeps
from infra.agents.tools.search import search_toolset

_VACANCY_INSTRUCTIONS = """\
You analyze job vacancies to extract structured signals for resume tailoring.

You have access to search tools:
- search_vacancy_chunks: Search the job vacancy by semantic similarity.
- search_resume_chunks: Search the candidate's resume by semantic similarity.

Use search_vacancy_chunks to find and analyze specific parts of the vacancy \
(requirements, responsibilities, qualifications, tech stack, etc.).

For each resume template section, extract relevant vacancy signals:
- title_signals: Role title variants, seniority indicators, domain keywords.
- about_signals: Key themes for professional summary, core competencies needed.
- skills_signals: All required and preferred skills, technologies, tools, methodologies.
- experience_signals: Experience types valued, years, domains, achievement patterns.
- education_signals: Required degrees, certifications, knowledge areas.

Then generate 5-10 targeted search queries to retrieve relevant resume chunks \
from a vector database. Queries should be specific and varied, covering:
- Technical skills and technology stack
- Role and responsibility patterns
- Domain and industry experience
- Achievement and impact patterns
"""

_EVIDENCE_INSTRUCTIONS = """\
You map resume evidence to vacancy requirements for resume tailoring.

You have access to search tools:
- search_resume_chunks: Search the candidate's resume by semantic similarity.
- search_vacancy_chunks: Search the job vacancy by semantic similarity.

Use these tools to find supporting evidence for each vacancy requirement signal.
Run multiple targeted queries covering skills, experience, education, achievements.

Classification rules:
- "direct": Evidence explicitly matches the requirement. Same skill, technology, \
role type, or achievement pattern.
- "adjacent": Evidence is closely related and transferable. Similar technology stack, \
related domain, comparable scope.
- "unsupported": No evidence in the resume chunks supports this requirement.

Map each evidence item to the target template field:
- "title" for job title and role positioning
- "about" for professional summary highlights
- "skills" for technical and soft skills
- "experience" for work history and achievements
- "education" for degrees and certifications

Every vacancy signal must have at least one evidence mapping, even if "unsupported".
Do not fabricate evidence. Be conservative in classification.
"""

_ASSEMBLY_INSTRUCTIONS = """\
You are a professional resume tailoring agent.
Your task is to assemble a tailored resume payload from validated evidence, \
matching the provided template structure.

STRICT RULES:
- Use ONLY "direct" and "adjacent" evidence from the evidence map.
- Direct evidence: use as-is, emphasizing alignment with the vacancy.
- Adjacent evidence: phrase conservatively within proven domain and skills.
- NEVER invent: companies, job titles, dates, certificates, metrics, \
leadership scope, or project ownership not in the evidence.
- Mild wording improvement is allowed, no strong exaggeration.
- Use <strong> tags in "about" for key technologies matching the vacancy.
- Generate the entire CV in the same language as the job vacancy.
- Preserve contact information exactly as in the evidence.
- Keep education entries unchanged from evidence.
- Prioritize skills appearing in vacancy requirements.
- Order experience to highlight the most relevant roles first.
- Each experience description bullet should be concise and impactful.
- The output structure must exactly match the provided JSON template.
"""


class CvGeneratorAgent(BaseAgent[CvGeneratorState, CvGeneratorResult]):
    def __init__(
        self,
        model_name: str,
        model_token: str,
        resume_metadata_dal: dal.ResumeMetadataDAL,
        job_metadata_dal: dal.JobMetadataDAL,
        max_retries: int = 2,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._resume_metadata_dal = resume_metadata_dal
        self._job_metadata_dal = job_metadata_dal
        model = OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(api_key=model_token),
        )
        self._vacancy_agent: Agent[SearchDeps] = Agent(
            model,
            deps_type=SearchDeps,
            instructions=_VACANCY_INSTRUCTIONS,
            toolsets=[search_toolset],
        )
        self._evidence_agent: Agent[SearchDeps] = Agent(
            model,
            deps_type=SearchDeps,
            instructions=_EVIDENCE_INSTRUCTIONS,
            toolsets=[search_toolset],
        )
        super().__init__(model, model_token, checkpointer=checkpointer)

    def _build_agent(self, model: Model | KnownModelName, model_token: str) -> Agent[Any, Any]:
        return Agent(
            model,
            instructions=_ASSEMBLY_INSTRUCTIONS,
        )

    def _build_graph(self, agent: Agent[Any, Any]) -> StateGraph:
        vacancy_agent = self._vacancy_agent
        evidence_agent = self._evidence_agent
        resume_dal = self._resume_metadata_dal
        job_dal = self._job_metadata_dal
        max_retries = self._max_retries

        async def validate_input(state: CvGeneratorState) -> dict:
            if not state["job_text"].strip():
                return {"error": "job_text is empty"}
            if not state["job_title"].strip():
                return {"error": "job_title is empty"}
            if not state["resume_id"].strip():
                return {"error": "resume_id is empty"}
            if not state["job_id"].strip():
                return {"error": "job_id is empty"}
            if not state["template_json"].strip():
                return {"error": "template_json is empty"}
            return {"error": None}

        async def analyze_vacancy(state: CvGeneratorState) -> dict:
            with logfire.span(
                "resume_tailoring.analyze_vacancy",
                job_title=state["job_title"],
            ):
                prompt = (
                    f"Job title: {state['job_title']}\n\n"
                    f"Job description:\n{state['job_text']}\n\n"
                    f"Target resume template structure:\n{state['template_json']}\n\n"
                    "Analyze this vacancy and extract signals for each template section. "
                    "Generate targeted search queries for resume evidence retrieval."
                )
                deps = SearchDeps(
                    resume_metadata_dal=resume_dal,
                    job_metadata_dal=job_dal,
                    resume_id=state["resume_id"],
                    job_id=state["job_id"],
                )
                try:
                    run_result = await vacancy_agent.run(prompt, output_type=VacancyAnalysis, deps=deps)
                    return {"vacancy_analysis": run_result.output, "error": None}
                except (httpx.ConnectError, httpx.TimeoutException, ModelAPIError) as exc:
                    logfire.error(
                        "resume_tailoring.analyze_vacancy connection failed",
                        error=str(exc),
                    )
                    return {"error": f"Connection failed: {exc}"}
                except (ModelHTTPError, UnexpectedModelBehavior) as exc:
                    logfire.error(
                        "resume_tailoring.analyze_vacancy failed",
                        error=str(exc),
                    )
                    return {"error": f"Vacancy analysis failed: {exc}"}

        async def build_evidence_map(state: CvGeneratorState) -> dict:
            with logfire.span("resume_tailoring.build_evidence_map"):
                analysis = state["vacancy_analysis"]
                if analysis is None:
                    return {"error": "Missing vacancy analysis"}
                signals = analysis.signals

                prompt = (
                    f"Vacancy signals:\n"
                    f"- Title: {', '.join(signals.title_signals)}\n"
                    f"- About: {', '.join(signals.about_signals)}\n"
                    f"- Skills: {', '.join(signals.skills_signals)}\n"
                    f"- Experience: {', '.join(signals.experience_signals)}\n"
                    f"- Education: {', '.join(signals.education_signals)}\n\n"
                    "Use the search tools to find resume and vacancy evidence for each signal. "
                    "Then map each vacancy requirement to the best evidence and classify."
                )
                deps = SearchDeps(
                    resume_metadata_dal=resume_dal,
                    job_metadata_dal=job_dal,
                    resume_id=state["resume_id"],
                    job_id=state["job_id"],
                )
                try:
                    run_result = await evidence_agent.run(prompt, output_type=EvidenceMap, deps=deps)
                    return {"evidence_map": run_result.output, "error": None}
                except (httpx.ConnectError, httpx.TimeoutException, ModelAPIError) as exc:
                    logfire.error(
                        "resume_tailoring.build_evidence_map connection failed",
                        error=str(exc),
                    )
                    return {"error": f"Connection failed: {exc}"}
                except (ModelHTTPError, UnexpectedModelBehavior) as exc:
                    logfire.error(
                        "resume_tailoring.build_evidence_map failed",
                        error=str(exc),
                    )
                    return {"error": f"Evidence mapping failed: {exc}"}

        async def assemble_payload(state: CvGeneratorState) -> dict:
            retry = state["retries"]
            with logfire.span(
                "resume_tailoring.assemble_payload",
                attempt=retry + 1,
                job_title=state["job_title"],
            ):
                evidence_map = state["evidence_map"]
                if evidence_map is None:
                    return {"tailored_result": None, "error": "Missing evidence map"}
                filtered = [item for item in evidence_map.items if item.evidence_type in ("direct", "adjacent")]
                if not filtered:
                    return {"tailored_result": None, "error": "No usable evidence found"}

                evidence_items_text = "\n".join(
                    f"- [{item.evidence_type}] {item.template_field}: " f"{item.requirement} → {item.evidence}"
                    for item in filtered
                )

                prompt = (
                    f"Job title: {state['job_title']}\n\n"
                    f"Job description:\n{state['job_text']}\n\n"
                    f"Evidence map (direct and adjacent only):\n{evidence_items_text}\n\n"
                    f"Target template:\n{state['template_json']}\n\n"
                    "Assemble the tailored resume payload using only the provided evidence. "
                    "Match the template structure exactly."
                )

                try:
                    run_result = await agent.run(prompt, output_type=ResumePayload)
                    logfire.info(
                        "resume_tailoring.assemble_payload succeeded",
                        job_title=state["job_title"],
                    )
                    return {"tailored_result": run_result.output, "error": None}
                except (httpx.ConnectError, httpx.TimeoutException, ModelAPIError) as exc:
                    logfire.error(
                        "resume_tailoring.assemble_payload connection failed",
                        error=str(exc),
                    )
                    return {
                        "tailored_result": None,
                        "error": f"Connection failed: {exc}",
                    }
                except ModelHTTPError as exc:
                    if exc.status_code == HTTPStatus.TOO_MANY_REQUESTS and retry < max_retries:
                        return {"retries": retry + 1, "tailored_result": None, "error": str(exc)}
                    logfire.error(
                        "resume_tailoring.assemble_payload model error",
                        status_code=exc.status_code,
                        error=str(exc),
                    )
                    return {
                        "tailored_result": None,
                        "error": f"Model API error (HTTP {exc.status_code}): {exc}",
                    }
                except UnexpectedModelBehavior as exc:
                    if retry < max_retries:
                        return {"retries": retry + 1, "tailored_result": None, "error": str(exc)}
                    return {
                        "tailored_result": None,
                        "error": f"Unexpected model behavior: {exc}",
                    }
                except Exception as exc:
                    if retry < max_retries:
                        logfire.warn(
                            "resume_tailoring.assemble_payload failed, retrying",
                            error=str(exc),
                        )
                        return {"retries": retry + 1, "tailored_result": None, "error": str(exc)}
                    logfire.error(
                        "resume_tailoring.assemble_payload exhausted retries",
                        error=str(exc),
                    )
                    return {
                        "tailored_result": None,
                        "error": f"Failed after {max_retries} retries: {exc}",
                    }

        def _route_or_end(next_node: str):
            def route(state: CvGeneratorState) -> str:
                if state.get("error"):
                    return END
                return next_node

            return route

        def should_retry_assembly(state: CvGeneratorState) -> str:
            if state.get("tailored_result"):
                return END
            if state.get("error") and state["retries"] < max_retries:
                return "assemble_payload"
            return END

        graph = StateGraph(CvGeneratorState)
        graph.add_node("validate_input", validate_input)
        graph.add_node("analyze_vacancy", analyze_vacancy)
        graph.add_node("build_evidence_map", build_evidence_map)
        graph.add_node("assemble_payload", assemble_payload)

        graph.add_edge(START, "validate_input")
        graph.add_conditional_edges(
            "validate_input",
            _route_or_end("analyze_vacancy"),
            {"analyze_vacancy": "analyze_vacancy", END: END},
        )
        graph.add_conditional_edges(
            "analyze_vacancy",
            _route_or_end("build_evidence_map"),
            {"build_evidence_map": "build_evidence_map", END: END},
        )
        graph.add_conditional_edges(
            "build_evidence_map",
            _route_or_end("assemble_payload"),
            {"assemble_payload": "assemble_payload", END: END},
        )
        graph.add_conditional_edges(
            "assemble_payload",
            should_retry_assembly,
            {"assemble_payload": "assemble_payload", END: END},
        )

        return graph

    def _build_initial_state(self, **kwargs: Any) -> CvGeneratorState:
        template_json = kwargs.get("template_json", "") or dumps(ResumePayload.model_json_schema(), ensure_ascii=False)
        return {
            "job_text": kwargs["job_text"],
            "job_title": kwargs["job_title"],
            "job_id": kwargs["job_id"],
            "resume_id": kwargs["resume_id"],
            "template_json": template_json,
            "vacancy_analysis": None,
            "evidence_map": None,
            "tailored_result": None,
            "error": None,
            "retries": 0,
        }

    def _parse_result(self, state: dict[str, Any]) -> CvGeneratorResult:
        if state.get("tailored_result"):
            return CvGeneratorResult(success=True, result=state["tailored_result"])
        return self._build_error_result()

    def _build_error_result(self) -> CvGeneratorResult:
        return CvGeneratorResult(success=False, result=None)

    async def run(self, thread_id: str | None = None, **kwargs: Any) -> CvGeneratorResult:
        config = {"configurable": {"thread_id": thread_id}} if thread_id else None
        initial_state = self._build_initial_state(**kwargs)
        try:
            async with self._agent, self._vacancy_agent, self._evidence_agent:
                final_state = await self._graph.ainvoke(initial_state, config=config)  # type: ignore[arg-type]
        except (httpx.ConnectError, httpx.TimeoutException, ModelAPIError) as exc:
            logfire.error(
                "{agent}.run connection failed",
                agent=type(self).__name__,
                error=str(exc),
            )
            return self._build_error_result()
        return self._parse_result(final_state)
