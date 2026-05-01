"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Enterprise Agentic AI Platform"
    environment: str = "development"
    log_level: str = "INFO"
    max_agent_iterations: int = 10

    # LLM
    anthropic_api_key: str
    openai_api_key: str = ""
    primary_model: str = "claude-sonnet-4-5"
    fallback_model: str = "gpt-4o"

    # Observability
    langsmith_api_key: str = ""
    langsmith_project: str = "enterprise-agentic-ai"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Database
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "enterprise_knowledge"

    # Auth
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # MCP Servers
    postgres_mcp_port: int = 8001
    document_mcp_port: int = 8002
    notification_mcp_port: int = 8003

    # External integrations
    github_token: str = ""
    notion_token: str = ""
    slack_bot_token: str = ""
    exa_api_key: str = ""

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-south-1"
    s3_bucket: str = "enterprise-ai-docs"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
