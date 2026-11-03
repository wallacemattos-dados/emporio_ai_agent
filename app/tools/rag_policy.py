import hashlib
import logging
import re
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TOP_K = 4
CHUNK_SIZE = 900
CHUNK_OVERLAP = 100
CABECALHO_PAGINA = "Empório da Música Manual de Políticas e Procedimentos"

RE_SECAO = re.compile(r"^(\d+)\.\s+(\S.*)$")
RE_SUBSECAO = re.compile(r"^(\d+)\.(\d+)\s+(\S.*)$")


def extrair_texto(pdf_path: Path) -> str:
    paginas = [p.extract_text(extraction_mode="layout") for p in PdfReader(pdf_path).pages]
    linhas = []
    for linha in "\n".join(paginas).splitlines():
        linha = linha.strip()
        if linha == CABECALHO_PAGINA or re.fullmatch(r"Página \d+", linha):
            continue
        linha = re.sub(r"^•\s+", "- ", linha)
        linha = re.sub(r"\s{2,}", " | ", linha)
        linhas.append(linha)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()


def separar_secoes(texto: str) -> list[tuple[str, str]]:
    blocos: list[tuple[str, list[str]]] = [("Capa", [])]
    principal = 0
    titulo_principal = ""
    for linha in texto.splitlines():
        secao = RE_SECAO.match(linha)
        subsecao = RE_SUBSECAO.match(linha)
        if secao and int(secao.group(1)) == principal + 1:
            principal = int(secao.group(1))
            titulo_principal = f"{principal}. {secao.group(2)}"
            blocos.append((titulo_principal, []))
        elif subsecao and int(subsecao.group(1)) == principal:
            titulo = f"{titulo_principal} > {subsecao.group(1)}.{subsecao.group(2)} {subsecao.group(3)}"
            blocos.append((titulo, []))
        else:
            blocos[-1][1].append(linha)
    resultado = [(titulo, "\n".join(corpo).strip()) for titulo, corpo in blocos]
    return [(titulo, corpo) for titulo, corpo in resultado if corpo]


def dividir_em_chunks(texto: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = []
    for titulo, corpo in separar_secoes(texto):
        for parte in splitter.split_text(corpo):
            chunks.append(Document(page_content=f"[{titulo}]\n{parte}", metadata={"secao": titulo}))
    return chunks


def nome_da_colecao(pdf_path: Path, modelo_embedding: str) -> str:
    hash_pdf = hashlib.sha1(pdf_path.read_bytes()).hexdigest()[:8]
    modelo = re.sub(r"[^a-zA-Z0-9._-]", "-", modelo_embedding)
    return f"politicas_{hash_pdf}_{modelo}"[:63].strip("-_.")


def construir_vectorstore(
    embeddings: Embeddings, pdf_path: Path, persist_dir: Path, nome_colecao: str
) -> Chroma:
    vectorstore = Chroma(
        collection_name=nome_colecao,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )
    if not vectorstore.get()["ids"]:
        vectorstore.add_documents(dividir_em_chunks(extrair_texto(pdf_path)))
    return vectorstore


@lru_cache
def _vectorstore() -> Chroma:
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model, api_key=settings.google_api_key
    )
    return construir_vectorstore(
        embeddings,
        settings.policies_pdf,
        settings.storage_dir / "chroma",
        nome_da_colecao(settings.policies_pdf, settings.embedding_model),
    )


def buscar_politicas(consulta: str, vectorstore: Chroma | None = None, k: int = TOP_K) -> str:
    documentos = (vectorstore or _vectorstore()).similarity_search(consulta, k=k)
    if not documentos:
        return "Nenhum trecho das políticas foi encontrado para essa consulta."
    return "\n\n---\n\n".join(doc.page_content for doc in documentos)


@tool
def consultar_politicas_loja(consulta: str) -> str:
    """Use esta ferramenta APENAS para buscar regras da loja: políticas de troca e devolução,
    garantia, formas de pagamento e parcelamento, frete e prazos de entrega, horários de
    funcionamento, endereço e contatos, regras de promoções. Passe a dúvida do cliente
    reescrita como uma consulta curta e objetiva (ex.: 'prazo para devolução por arrependimento').
    """
    try:
        return buscar_politicas(consulta)
    except Exception:
        logger.exception("Falha ao consultar as políticas")
        return "ERRO: não foi possível consultar as políticas agora."