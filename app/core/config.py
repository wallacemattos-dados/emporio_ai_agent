from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: SecretStr
    llm_model: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)

    data_dir: Path = BASE_DIR / "data"
    storage_dir: Path = BASE_DIR / "storage"

    @property
    def policies_pdf(self) -> Path:
        return self.data_dir / "politicas_da_loja.pdf"


@lru_cache
def get_settings() -> Settings:
    return Settings()