import asyncio
import uuid
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
from pydantic_ai.usage import UsageLimits

from core import repos
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

Workflow (STRICT — follow exactly):
1. Call search_vacancy_chunks ONCE with a broad query covering all sections \
(requirements, skills, responsibilities, tech stack, seniority, education).
2. Analyse the returned chunks. Do NOT make additional search calls.
3. Immediately produce the structured output.

From the retrieved chunks, extract signals for each resume template section:
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

All relevant resume chunks and vacancy chunks are provided in the prompt.
Do NOT use any search tools — classify only from the provided context.

Classification rules:
- "direct": Evidence explicitly matches the requirement. Same skill, technology, \
role type, or achievement pattern.
- "adjacent": Evidence is closely related and transferable. Similar technology stack, \
related domain, comparable scope.
- "unsupported": No evidence in the provided chunks supports this requirement.

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
- Generate the entire CV in the language specified in the prompt.
- Transliterate the candidate's full name into the target language script \
(e.g., Latin for English).
- Translate the candidate's contact information into the target language, \
including location names.
- Translate the candidate's education entries (degree names, institution names, \
periods) into the target language. Transliterate institution names if needed.
- Include ALL experience entries from the candidate's resume — never omit any.
- Translate all experience position titles into the target language. \
Transliterate company names into the target language script.
- Use the evidence map to tailor experience descriptions to the vacancy, but keep every job period.
- Translate ALL text into the target language specified in the prompt.
- Use <strong> tags inside experience description bullets to highlight key \
technologies or metrics that match the vacancy.
- Prioritize skills appearing in vacancy requirements.
- Order experience to highlight the most relevant roles first.
- Each experience description bullet should be concise and impactful.
- The output structure must exactly match the provided JSON template.
"""

_ANALYZE_VACANCY_PROMPT = """\
Job title: {job_title}

Job description:
{job_text}

Target resume template structure:
{template_json}

Analyze this vacancy and extract signals for each template section.
Generate targeted search queries for resume evidence retrieval.
"""

_BUILD_EVIDENCE_MAP_PROMPT = """\
Vacancy signals:
- Title: {title_signals}
- About: {about_signals}
- Skills: {skills_signals}
- Experience: {experience_signals}
- Education: {education_signals}

Resume chunks:
{resume_chunks}

Vacancy chunks:
{vacancy_chunks}

Map each vacancy signal to the best evidence from the chunks above and classify.
"""

_ASSEMBLE_PAYLOAD_PROMPT = """\
Candidate full name: {full_name}

Candidate contacts: {contacts}

Candidate education: {education}

Candidate experience (ALL entries must appear in the output): {experience}

Target output language: {vacancy_language}

Job title: {job_title}

Job description:
{job_text}

Evidence map (direct and adjacent only):
{evidence_items_text}

Target template:
{template_json}

Assemble the tailored resume payload using only the provided evidence.
Match the template structure exactly.
Transliterate the full name to {vacancy_language} script.
Translate ALL text — including location, job titles, company names,
institution names, education, about, skills, and experience — into {vacancy_language}.
Transliterate proper nouns (company names, institution names) if a direct translation is not available.
"""


class CvGeneratorAgent(BaseAgent[CvGeneratorState, CvGeneratorResult]):
    def __init__(
        self,
        model_name: str,
        model_token: str,
        resume_metadata_repo: repos.ResumeMetadataRepository,
        job_metadata_repo: repos.JobMetadataRepository,
        max_retries: int = 2,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._resume_metadata_repo = resume_metadata_repo
        self._job_metadata_repo = job_metadata_repo
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
        self._evidence_agent: Agent[None] = Agent(
            model,
            instructions=_EVIDENCE_INSTRUCTIONS,
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
        resume_repo = self._resume_metadata_repo
        job_repo = self._job_metadata_repo
        max_retries = self._max_retries

        async def validate_input(state: CvGeneratorState) -> dict:
            if not state["user_id"].strip():
                return {"error": "user_id is empty"}
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
                prompt = _ANALYZE_VACANCY_PROMPT.format(
                    job_title=state["job_title"],
                    job_text=state["job_text"],
                    template_json=state["template_json"],
                )
                deps = SearchDeps(
                    resume_metadata_repo=resume_repo,
                    job_metadata_repo=job_repo,
                    user_id=state["user_id"],
                    resume_id=state["resume_id"],
                    job_id=state["job_id"],
                )
                try:
                    run_result = await vacancy_agent.run(
                        prompt,
                        output_type=VacancyAnalysis,
                        deps=deps,
                        usage_limits=UsageLimits(request_limit=3),
                    )
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
                except Exception as exc:
                    logfire.error(
                        "resume_tailoring.analyze_vacancy unexpected error",
                        error=str(exc),
                    )
                    return {"error": f"Unexpected error: {exc}"}

        async def build_evidence_map(state: CvGeneratorState) -> dict:
            with logfire.span("resume_tailoring.build_evidence_map"):
                analysis = state["vacancy_analysis"]
                if analysis is None:
                    return {"error": "Missing vacancy analysis"}
                signals = analysis.signals

                user_uuid = uuid.UUID(state["user_id"])
                resume_uuid = uuid.UUID(state["resume_id"])
                job_uuid = uuid.UUID(state["job_id"])

                resume_tasks = [
                    resume_repo.search_by_text(
                        query=q,
                        resume_id=resume_uuid,
                        user_id=user_uuid,
                        limit=4,
                    )
                    for q in analysis.search_queries
                ]
                vacancy_search = job_repo.search_by_text(
                    query=" ".join(signals.skills_signals[:8]),
                    job_id=job_uuid,
                    user_id=user_uuid,
                    limit=5,
                )
                all_results = await asyncio.gather(*resume_tasks, vacancy_search)

                seen: set[str] = set()
                resume_chunks: list[str] = []
                for chunk_list in all_results[:-1]:
                    for chunk in chunk_list:
                        if chunk not in seen:
                            seen.add(chunk)
                            resume_chunks.append(chunk)
                vacancy_chunks = list(dict.fromkeys(all_results[-1]))

                prompt = _BUILD_EVIDENCE_MAP_PROMPT.format(
                    title_signals=", ".join(signals.title_signals),
                    about_signals=", ".join(signals.about_signals),
                    skills_signals=", ".join(signals.skills_signals),
                    experience_signals=", ".join(signals.experience_signals),
                    education_signals=", ".join(signals.education_signals),
                    resume_chunks="\n---\n".join(resume_chunks),
                    vacancy_chunks="\n---\n".join(vacancy_chunks),
                )
                try:
                    run_result = await evidence_agent.run(
                        prompt,
                        output_type=EvidenceMap,
                    )
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
                except Exception as exc:
                    logfire.error(
                        "resume_tailoring.build_evidence_map unexpected error",
                        error=str(exc),
                    )
                    return {"error": f"Unexpected error: {exc}"}

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

                meta = state["metadata"]

                prompt = _ASSEMBLE_PAYLOAD_PROMPT.format(
                    full_name=meta.full_name,
                    contacts=dumps(meta.contacts, ensure_ascii=False),
                    education=dumps(meta.education, ensure_ascii=False),
                    experience=dumps(meta.experience, ensure_ascii=False),
                    vacancy_language=meta.vacancy_language,
                    job_title=state["job_title"],
                    job_text=state["job_text"],
                    evidence_items_text=evidence_items_text,
                    template_json=state["template_json"],
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
            "user_id": kwargs["user_id"],
            "metadata": kwargs["metadata"],
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
