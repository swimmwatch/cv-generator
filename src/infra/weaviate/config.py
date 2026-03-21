from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class WeaviateSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="weaviate_")

    http_host: str = "localhost"
    http_port: int = 8080
    grpc_host: str = "localhost"
    grpc_port: int = 50051
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
