import json
import re
from pathlib import Path

import duckdb
from langchain_core.tools import tool

from app.core.config import get_settings

MAX_LINHAS = 30
DESCONTO_PIX = 0.05

STATUS_PEDIDO = {
    "pending": "pendente (aguardando confirmação)",
    "confirmed": "confirmado",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}

PEDIDO_NAO_ENCONTRADO = (
    "Não encontrei um pedido com esse número e e-mail. Peça ao cliente para "
    "conferir os dados do cadastro ou procurar a equipe da loja."
)

CATEGORIAS = (
    "Guitarras, Baixos, Baterias e Percussão, Teclados e Pianos, Violões, "
    "Instrumentos de Sopro (Madeiras), Instrumentos de Sopro (Metais), "
    "Cordas Orquestrais, Ukuleles"
)

DESCRICAO_CATALOGO = f"""Use esta ferramenta APENAS para buscar informações sobre produtos \
(preço, estoque, disponibilidade) e promoções ativas. Para pedidos, use consultar_status_pedido.

Executa UMA consulta SQL SELECT (DuckDB, somente leitura) na view `catalogo`, com uma linha por produto.
Colunas:
- product_id, nome (marca e modelo), descricao, specs (texto com características)
- categoria (valores exatos: {CATEGORIAS})
- preco_tabela_brl, estoque, status ('active', 'discontinued' ou 'coming_soon')
- disponivel: true somente se status = 'active' E estoque > 0
- desconto_ativo_percent, promocao, preco_promocional_brl: NULL quando NÃO há promoção ativa
- preco_pix_brl: preço à vista no PIX (5% off); NULL quando o produto está em promoção
Dicas: busque o nome com ILIKE e partes do nome (nome ILIKE '%takamine%' AND nome ILIKE '%gd20%'); \
para "disponíveis" filtre disponivel = true; compare preços com COALESCE(preco_promocional_brl, preco_tabela_brl); \
use LIMIT. Envie apenas uma instrução, sem ponto e vírgula."""


def _conectar(data_dir: Path, tabelas: tuple[str, ...]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA raw")
    for nome in tabelas:
        caminho = (data_dir / f"{nome}.csv").as_posix().replace("'", "''")
        con.execute(
            f"CREATE TABLE raw.{nome} AS SELECT * FROM read_csv('{caminho}', header = true)"
        )
    return con


def _criar_catalogo(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        f"""
        CREATE VIEW catalogo AS
        SELECT
            p.product_id,
            p.name AS nome,
            c.name AS categoria,
            p.description AS descricao,
            p.price_brl AS preco_tabela_brl,
            p.stock_quantity AS estoque,
            p.status,
            (p.status = 'active' AND p.stock_quantity > 0) AS disponivel,
            pr.desconto AS desconto_ativo_percent,
            pr.nome_promocao AS promocao,
            CASE WHEN pr.desconto IS NOT NULL
                 THEN ROUND(p.price_brl * (1 - pr.desconto / 100.0), 2) END AS preco_promocional_brl,
            CASE WHEN pr.desconto IS NULL
                 THEN ROUND(p.price_brl * {1 - DESCONTO_PIX}, 2) END AS preco_pix_brl,
            p.specs
        FROM raw.products p
        LEFT JOIN raw.categories c ON c.category_id = p.category_id
        LEFT JOIN (
            SELECT product_id,
                   MAX(discount_percent) AS desconto,
                   arg_max(description, discount_percent) AS nome_promocao
            FROM raw.promotions
            WHERE is_active = 1
            GROUP BY product_id
        ) pr ON pr.product_id = p.product_id
        """
    )


def _trancar(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")


def _validar_sql(sql: str) -> str | None:
    if not sql:
        return "a consulta está vazia."
    sem_literais = re.sub(r"'(?:[^']|'')*'", "''", sql)
    if ";" in sem_literais:
        return "envie uma única instrução SQL, sem ponto e vírgula."
    if not re.match(r"(?is)^\s*(select|with)\b", sql):
        return "apenas consultas SELECT são permitidas."
    return None


def consultar_catalogo(sql: str, data_dir: Path | None = None) -> str:
    data_dir = data_dir or get_settings().data_dir
    sql_limpo = sql.strip().rstrip(";").strip()
    problema = _validar_sql(sql_limpo)
    if problema:
        return f"ERRO: {problema}"
    try:
        con = _conectar(data_dir, ("products", "categories", "promotions"))
        _criar_catalogo(con)
        _trancar(con)
    except duckdb.Error as e:
        return f"ERRO: não foi possível carregar os dados da loja ({e})."
    try:
        cur = con.execute(sql_limpo)
        colunas = [d[0] for d in cur.description]
        linhas = cur.fetchmany(MAX_LINHAS + 1)
    except duckdb.Error as e:
        return f"ERRO ao executar a consulta: {e}. Corrija o SQL e tente novamente."
    finally:
        con.close()
    resultado = {
        "linhas": [dict(zip(colunas, linha)) for linha in linhas[:MAX_LINHAS]],
        "truncado": len(linhas) > MAX_LINHAS,
    }
    return json.dumps(resultado, ensure_ascii=False, default=str)


def _traduzir_pagamento(valor: str | None) -> str | None:
    if valor is None:
        return None
    parcelado = re.fullmatch(r"credit_(\d+)x", valor)
    if parcelado:
        return f"cartão de crédito em {parcelado.group(1)}x"
    return {"pix": "PIX", "debit": "cartão de débito", "boleto": "boleto"}.get(valor, valor)


def buscar_pedido(numero_pedido: int, email: str, data_dir: Path | None = None) -> str:
    data_dir = data_dir or get_settings().data_dir
    try:
        con = _conectar(data_dir, ("orders", "order_items", "customers", "products"))
    except duckdb.Error as e:
        return f"ERRO: não foi possível carregar os dados da loja ({e})."
    try:
        pedido = con.execute(
            """
            SELECT o.status, o.order_date, o.total_brl, o.payment_method,
                   o.tracking_code, o.estimated_delivery, o.notes, c.email
            FROM raw.orders o
            JOIN raw.customers c ON c.customer_id = o.customer_id
            WHERE o.order_id = ?
            """,
            [numero_pedido],
        ).fetchone()
        if pedido is None or (pedido[7] or "").strip().lower() != email.strip().lower():
            return PEDIDO_NAO_ENCONTRADO
        itens = con.execute(
            """
            SELECT p.name, oi.quantity
            FROM raw.order_items oi
            JOIN raw.products p ON p.product_id = oi.product_id
            WHERE oi.order_id = ?
            """,
            [numero_pedido],
        ).fetchall()
    except duckdb.Error as e:
        return f"ERRO ao consultar o pedido: {e}."
    finally:
        con.close()
    resultado = {
        "numero_pedido": numero_pedido,
        "status": STATUS_PEDIDO.get(pedido[0], pedido[0]),
        "data_pedido": pedido[1],
        "total_brl": pedido[2],
        "pagamento": _traduzir_pagamento(pedido[3]),
        "codigo_rastreio": pedido[4],
        "previsao_entrega": pedido[5],
        "observacoes": pedido[6],
        "itens": [{"produto": nome, "quantidade": qtd} for nome, qtd in itens],
    }
    return json.dumps(resultado, ensure_ascii=False, default=str)


@tool(description=DESCRICAO_CATALOGO)
def consultar_banco_dados_loja(sql: str) -> str:
    return consultar_catalogo(sql)


@tool
def consultar_status_pedido(numero_pedido: int, email_cadastro: str) -> str:
    """Consulta o status de UM pedido (itens, pagamento, rastreio, previsão de entrega).
    Exige o número do pedido e o e-mail do cadastro do cliente; sem os dois, não use a ferramenta.
    """
    return buscar_pedido(numero_pedido, email_cadastro)