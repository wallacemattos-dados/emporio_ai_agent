import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_falha_quando_variaveis_obrigatorias_faltam(monkeypatch):
    for nome in ("GOOGLE_API_KEY", "LLM_MODEL", "EMBEDDING_MODEL"):
        monkeypatch.delenv(nome)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_nome_de_modelo_vazio_e_rejeitado(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_chave_nao_aparece_na_representacao_do_objeto():
    assert "chave-falsa-de-teste" not in repr(Settings(_env_file=None))