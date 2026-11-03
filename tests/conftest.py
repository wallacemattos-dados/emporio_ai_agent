import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def ambiente_falso(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-falsa-de-teste")
    monkeypatch.setenv("LLM_MODEL", "modelo-falso")
    monkeypatch.setenv("EMBEDDING_MODEL", "embedding-falso")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()