import uuid
from collections.abc import Iterator

import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from core.errors.resumes import InvalidResumeError
from infra.agents.resume_parser import ResumeParser
from infra.agents.resume_parser import ResumeParseResult
from infra.agents.schemas.resume import ResumeEducation
from infra.agents.schemas.resume import ResumeExperience
from infra.agents.schemas.resume import ResumePayload


@pytest.fixture
def resume_parser() -> Iterator[ResumeParser]:
    prev = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield ResumeParser(model_name="test", model_token="test")  # noqa: S106
    models.ALLOW_MODEL_REQUESTS = prev


class TestResumeParserChunk:
    def _chunk(self, resume_parser: ResumeParser, payload: ResumePayload, **kwargs):
        return resume_parser._chunk(
            resume_id=kwargs.get("resume_id", uuid.uuid4()),
            user_id=kwargs.get("user_id", uuid.uuid4()),
            resume_text=kwargs.get("resume_text", "text"),
            payload=payload,
        )

    def test_always_includes_full_resume(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True, full_name="John Doe", title="Dev", about="", skills=[], experience=[], education=[]
        )
        resume_id = uuid.uuid4()
        user_id = uuid.uuid4()

        chunks = self._chunk(resume_parser, payload, resume_id=resume_id, user_id=user_id, resume_text="raw text")

        sections = [c.section for c in chunks]
        assert "full_resume" in sections
        full = next(c for c in chunks if c.section == "full_resume")
        assert full.content == "raw text"
        assert full.resume_id == str(resume_id)
        assert full.user_id == str(user_id)

    def test_includes_about_section(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True,
            full_name="Jane Smith",
            title="Engineer",
            about="Experienced engineer",
            skills=[],
            experience=[],
            education=[],
        )

        chunks = self._chunk(resume_parser, payload)

        about = [c for c in chunks if c.section == "about"]
        assert len(about) == 1
        assert about[0].content == "Experienced engineer"

    def test_skips_about_when_empty(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True, full_name="A B", title="Dev", about="", skills=[], experience=[], education=[]
        )

        chunks = self._chunk(resume_parser, payload)

        assert not any(c.section == "about" for c in chunks)

    def test_includes_skills_section(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True,
            full_name="A B",
            title="Dev",
            about="",
            skills=["Python", "Go", "Docker"],
            experience=[],
            education=[],
        )

        chunks = self._chunk(resume_parser, payload)

        skills = [c for c in chunks if c.section == "skills"]
        assert len(skills) == 1
        assert skills[0].content == "Python, Go, Docker"

    def test_skips_skills_when_empty(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True, full_name="A B", title="Dev", about="", skills=[], experience=[], education=[]
        )

        chunks = self._chunk(resume_parser, payload)

        assert not any(c.section == "skills" for c in chunks)

    def test_creates_chunk_per_experience(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True,
            full_name="A B",
            title="Dev",
            about="",
            skills=[],
            experience=[
                ResumeExperience(
                    position="Senior Dev",
                    company="Acme",
                    period="2020-2023",
                    description=["Built systems"],
                    stack=["Python", "FastAPI"],
                ),
                ResumeExperience(
                    position="Junior Dev",
                    company="StartupX",
                    period="2018-2020",
                    description=["Wrote code"],
                    stack=[],
                ),
            ],
            education=[],
        )

        chunks = self._chunk(resume_parser, payload)

        exp_chunks = [c for c in chunks if c.section == "experience"]
        assert len(exp_chunks) == 2
        assert "Senior Dev at Acme" in exp_chunks[0].content
        assert "Technologies: Python, FastAPI" in exp_chunks[0].content
        assert "Junior Dev at StartupX" in exp_chunks[1].content
        assert exp_chunks[0].metadata["company"] == "Acme"
        assert exp_chunks[1].metadata["position"] == "Junior Dev"

    def test_creates_chunk_per_education(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True,
            full_name="A B",
            title="Dev",
            about="",
            skills=[],
            experience=[],
            education=[
                ResumeEducation(period="2014-2018", degree="BSc CS", institution="MIT"),
            ],
        )

        chunks = self._chunk(resume_parser, payload)

        edu_chunks = [c for c in chunks if c.section == "education"]
        assert len(edu_chunks) == 1
        assert "BSc CS" in edu_chunks[0].content
        assert "MIT" in edu_chunks[0].content

    def test_splits_full_name_into_first_last(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True,
            full_name="Dmitry Krasnov",
            title="DevOps",
            about="Summary",
            skills=[],
            experience=[],
            education=[],
        )

        chunks = self._chunk(resume_parser, payload)

        for chunk in chunks:
            assert chunk.metadata["first_name"] == "Dmitry"
            assert chunk.metadata["last_name"] == "Krasnov"

    def test_handles_single_name(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True,
            full_name="Madonna",
            title="Singer",
            about="",
            skills=[],
            experience=[],
            education=[],
        )

        chunks = self._chunk(resume_parser, payload)

        for chunk in chunks:
            assert chunk.metadata["first_name"] == "Madonna"
            assert chunk.metadata["last_name"] == ""

    def test_total_chunk_count(self, resume_parser: ResumeParser) -> None:
        payload = ResumePayload(
            is_resume=True,
            full_name="A B",
            title="Dev",
            about="Summary",
            skills=["Python"],
            experience=[
                ResumeExperience(position="Dev", company="Co", period="2020-2023", description=["Did stuff"]),
            ],
            education=[
                ResumeEducation(period="2016-2020", degree="BSc", institution="Uni"),
            ],
        )

        chunks = self._chunk(resume_parser, payload)

        # full_resume + about + skills + 1 experience + 1 education = 5
        assert len(chunks) == 5


class TestResumeParserParse:
    @staticmethod
    def _valid_model() -> TestModel:
        return TestModel(
            custom_output_args=ResumePayload(
                is_resume=True,
                full_name="a b",
                title="Dev",
                about="",
                skills=[],
                experience=[],
            )
        )

    async def test_returns_parse_result(self, resume_parser: ResumeParser) -> None:
        resume_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with resume_parser._agent.override(model=self._valid_model()):
            result = await resume_parser.parse(
                resume_text="John Doe, Software Engineer",
                resume_id=resume_id,
                user_id=user_id,
            )

        assert isinstance(result, ResumeParseResult)
        assert isinstance(result.title, str)
        assert len(result.chunks) > 0

    async def test_full_resume_chunk_has_original_text(self, resume_parser: ResumeParser) -> None:
        resume_text = "Jane Smith\nData Scientist\nExpert in ML"
        resume_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with resume_parser._agent.override(model=self._valid_model()):
            result = await resume_parser.parse(
                resume_text=resume_text,
                resume_id=resume_id,
                user_id=user_id,
            )

        full = next(c for c in result.chunks if c.section == "full_resume")
        assert full.content == resume_text
        assert full.resume_id == str(resume_id)
        assert full.user_id == str(user_id)

    async def test_chunks_have_correct_ids(self, resume_parser: ResumeParser) -> None:
        resume_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with resume_parser._agent.override(model=self._valid_model()):
            result = await resume_parser.parse(
                resume_text="Some resume",
                resume_id=resume_id,
                user_id=user_id,
            )

        for chunk in result.chunks:
            assert chunk.resume_id == str(resume_id)
            assert chunk.user_id == str(user_id)

    async def test_raises_error_for_non_resume(self, resume_parser: ResumeParser) -> None:
        custom_result = ResumePayload(
            is_resume=False,
            full_name="",
            title="",
            about="",
            skills=[],
            experience=[],
        )

        with resume_parser._agent.override(model=TestModel(custom_output_args=custom_result)):
            with pytest.raises(InvalidResumeError):
                await resume_parser.parse(
                    resume_text="Take 2 cups of flour...",
                    resume_id=uuid.uuid4(),
                    user_id=uuid.uuid4(),
                )
