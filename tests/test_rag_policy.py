import re

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.core.config import get_settings
from app.tools import rag_policy
from app.tools.rag_policy import (
    buscar_politicas,
    construir_vectorstore,
    dividir_em_chunks,
    extrair_texto,
    nome_da_colecao,
    separar_secoes,
)


@pytest.fixture
def texto():
    return extrair_texto(get_settings().policies_pdf)


def test_secoes_seguem_a_estrutura_do_manual(texto):
    titulos = [titulo for titulo, _ in separar_secoes(texto)]
    assert any(t.endswith("4.1 Direito de Arrependimento (Compras Online)") for t in titulos)
    assert any(t.startswith("2. Horário de Funcionamento") for t in titulos)


def test_lista_numerada_do_fluxo_de_atendimento_nao_vira_secao(texto):
    titulos = [titulo for titulo, _ in separar_secoes(texto)]
    assert not any("Saudação" in t or "Entendimento" in t for t in titulos)


def test_chunk_de_arrependimento_contem_o_prazo(texto):
    chunks = dividir_em_chunks(texto)
    arrependimento = [c for c in chunks if "4.1" in c.metadata["secao"]]
    assert arrependimento
    assert "7 (sete) dias" in arrependimento[0].page_content


def test_ruido_de_pagina_e_removido(texto):
    assert "Manual de Políticas e Procedimentos" not in texto.replace("MANUAL DE POLÍTICAS E PROCEDIMENTOS", "")
    assert not re.search(r"^Página \d+$", texto, flags=re.MULTILINE)


def test_nenhum_chunk_passa_do_limite_muito_acima_do_tamanho(texto):
    chunks = dividir_em_chunks(texto)
    assert 15 <= len(chunks) <= 60
    assert all(len(c.page_content) < rag_policy.CHUNK_SIZE + 200 for c in chunks)


def test_nome_da_colecao_e_valido_para_o_chroma_e_muda_com_o_modelo():
    pdf = get_settings().policies_pdf
    a = nome_da_colecao(pdf, "gemini-embedding-001")
    b = nome_da_colecao(pdf, "outro-modelo")
    assert re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,61}[a-zA-Z0-9]", a)
    assert a != b


def test_indice_e_criado_uma_vez_e_reaproveitado(tmp_path, texto):
    embeddings = DeterministicFakeEmbedding(size=16)
    pdf = get_settings().policies_pdf
    esperado = len(dividir_em_chunks(texto))

    primeiro = construir_vectorstore(embeddings, pdf, tmp_path, "teste")
    assert len(primeiro.get()["ids"]) == esperado

    segundo = construir_vectorstore(embeddings, pdf, tmp_path, "teste")
    assert len(segundo.get()["ids"]) == esperado


def test_busca_devolve_no_maximo_k_trechos(tmp_path):
    vectorstore = construir_vectorstore(
        DeterministicFakeEmbedding(size=16), get_settings().policies_pdf, tmp_path, "teste"
    )
    resposta = buscar_politicas("troca", vectorstore=vectorstore, k=3)
    assert resposta.count("---") == 2


def test_ferramenta_devolve_erro_textual_em_vez_de_quebrar(monkeypatch):
    def falha():
        raise RuntimeError("embeddings fora do ar")

    monkeypatch.setattr(rag_policy, "_vectorstore", falha)
    assert rag_policy.consultar_politicas_loja.invoke({"consulta": "troca"}).startswith("ERRO")