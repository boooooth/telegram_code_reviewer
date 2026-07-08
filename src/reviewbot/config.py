from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str
    telegram_allowed_user_id: int

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    deepseek_api_key: str | None = None

    ollama_base_url: str | None = None

    agent_model_provider: str = "anthropic"
    agent_model_name: str = "claude-sonnet-4-5"
    summarizer_model_provider: str = "anthropic"
    summarizer_model_name: str = "claude-haiku-4-5"
    judge_model_provider: str = "anthropic"
    judge_model_name: str = "claude-haiku-4-5"

    max_working_memory_messages: int = 6

    github_token: str | None = None
    max_pr_files: int = 10
    max_pr_file_bytes: int = 50_000
    max_pr_total_context_bytes: int = 150_000
    max_pr_diff_bytes: int = 150_000

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://localhost:3000"

    data_dir: Path = Path("./data")

    @property
    def episodic_db_path(self) -> Path:
        return self.data_dir / "episodic.db"

    @property
    def checkpoint_db_path(self) -> Path:
        return self.data_dir / "checkpoints.db"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"


settings = Settings()  # type: ignore[call-arg]  # fields are populated from .env, not constructor args
settings.data_dir.mkdir(parents=True, exist_ok=True)
