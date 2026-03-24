from pydantic import SecretStr
from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class MCPSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="agents_mcp_")

    proxy_url: str
    proxy_auth_token: SecretStr


class AgentModelSettings(BaseSettings):
    model_name: str
    model_token: SecretStr


class ResumeParserSettings(AgentModelSettings):
    model_config = SettingsConfig(env_prefix="agents_resume_parser_")

    temperature: float = 0.0
    max_tokens: int = 16384
    timeout: float = 60.0
    top_p: float = 1.0


class JobParserSettings(AgentModelSettings):
    model_config = SettingsConfig(env_prefix="agents_job_parser_")

    max_tokens: int = 16384
    timeout: float = 60.0


class CvGeneratorSettings(AgentModelSettings):
    model_config = SettingsConfig(env_prefix="agents_cv_generator_")


class ChatSettings(AgentModelSettings):
    model_config = SettingsConfig(env_prefix="agents_chat_")


class AgentsSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="agents_")

    mcp: MCPSettings = MCPSettings()
    resume_parser: ResumeParserSettings = ResumeParserSettings()
    job_parser: JobParserSettings = JobParserSettings()
    cv_generator: CvGeneratorSettings = CvGeneratorSettings()
    chat: ChatSettings = ChatSettings()
