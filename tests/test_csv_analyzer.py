import json

import duckdb
import pytest

from app.core.config import get_settings
from app.tools.csv_analyzer import (
    CATEGORIAS,
    MAX_LINHAS,
    PEDIDO_NAO_ENCONTRADO,
    buscar_pedido,
    consultar_catalogo,
)


def consultar(sql: str) -> dict:
    return json.loads(consultar_catalogo(sql))


def por_id(product_id: int) -> dict:
    return consultar(f"SELECT * FROM catalogo WHERE product_id = {product_id}")["linhas"][0]


def email_do_cliente_do_pedido(order_id: int) -> str:
    data = get_settings().data_dir
    return duckdb.sql(
        f"""SELECT c.email FROM '{(data / "orders.csv").as_posix()}' o
            JOIN '{(data / "customers.csv").as_posix()}' c USING (customer_id)
            WHERE o.order_id = {order_id}"""
    ).fetchall()[0][0]


# ---------- catálogo ----------

def test_disponivel_exige_status_ativo_e_estoque():
    assert por_id(95)["disponivel"] is True        # Takamine GD20: ativo, estoque 5
    assert por_id(96)["disponivel"] is False       # ativo, estoque 0
    assert por_id(136)["disponivel"] is False      # descontinuado, estoque 13
    assert por_id(130)["disponivel"] is False      # em breve, estoque 2


def test_promocao_inativa_nao_gera_desconto():
    takamine = por_id(95)
    assert takamine["preco_tabela_brl"] == 2199.0
    assert takamine["desconto_ativo_percent"] is None
    assert takamine["preco_promocional_brl"] is None
    assert takamine["preco_pix_brl"] == 2089.05


def test_promocao_ativa_tem_preco_promocional_e_sem_pix():
    produto = por_id(94)                            # promoção ativa de 8%
    assert produto["desconto_ativo_percent"] == 8
    assert produto["preco_promocional_brl"] == round(produto["preco_tabela_brl"] * 0.92, 2)
    assert produto["preco_pix_brl"] is None


def test_categorias_da_descricao_batem_com_o_csv():
    data = get_settings().data_dir
    nomes = duckdb.sql(
        f"SELECT name FROM '{(data / 'categories.csv').as_posix()}'"
    ).fetchall()
    for (nome,) in nomes:
        assert nome in CATEGORIAS


def test_limita_o_numero_de_linhas():
    resultado = consultar("SELECT product_id FROM catalogo")
    assert len(resultado["linhas"]) == MAX_LINHAS
    assert resultado["truncado"] is True


# ---------- segurança do SQL ----------

@pytest.mark.parametrize(
    "sql",
    [
        "DROP VIEW catalogo",
        "DELETE FROM raw.products",
        "SELECT 1; SELECT 2",
        "",
    ],
)
def test_rejeita_sql_que_nao_e_um_select_simples(sql):
    assert consultar_catalogo(sql).startswith("ERRO")


def test_ponto_e_virgula_dentro_de_texto_e_permitido():
    resultado = consultar("SELECT product_id FROM catalogo WHERE nome ILIKE '%a;b%'")
    assert resultado["linhas"] == []


def test_nao_le_arquivos_do_disco_nem_dados_de_clientes():
    caminho = (get_settings().data_dir / "customers.csv").as_posix()
    resposta = consultar_catalogo(f"SELECT * FROM read_csv('{caminho}')")
    assert resposta.startswith("ERRO")
    assert "@" not in resposta


def test_tabelas_de_clientes_e_pedidos_nao_existem_no_banco_do_llm():
    assert consultar_catalogo("SELECT * FROM raw.customers").startswith("ERRO")
    assert consultar_catalogo("SELECT * FROM raw.orders").startswith("ERRO")


def test_erro_de_sql_volta_como_texto_para_o_llm():
    resposta = consultar_catalogo("SELECT coluna_que_nao_existe FROM catalogo")
    assert resposta.startswith("ERRO ao executar")


def test_pasta_de_dados_inexistente_nao_quebra(tmp_path):
    resposta = consultar_catalogo("SELECT 1", data_dir=tmp_path)
    assert resposta.startswith("ERRO: não foi possível carregar")


# ---------- pedidos ----------

def test_pedido_com_email_correto_traduz_status_e_lista_itens():
    resposta = json.loads(buscar_pedido(1, email_do_cliente_do_pedido(1)))
    assert resposta["status"] == "entregue"
    assert resposta["pagamento"] == "PIX"
    assert resposta["itens"][0]["quantidade"] == 1
    assert resposta["codigo_rastreio"] == "BRAB1234567BR"


def test_email_e_comparado_sem_diferenca_de_maiusculas_ou_espacos():
    email = "  " + email_do_cliente_do_pedido(1).upper() + " "
    assert "status" in json.loads(buscar_pedido(1, email))


def test_email_errado_e_pedido_inexistente_dao_a_mesma_resposta():
    assert buscar_pedido(1, "outra.pessoa@exemplo.com") == PEDIDO_NAO_ENCONTRADO
    assert buscar_pedido(99999, "qualquer@exemplo.com") == PEDIDO_NAO_ENCONTRADO


def test_resposta_do_pedido_nao_devolve_o_email_do_cliente():
    email = email_do_cliente_do_pedido(1)
    assert email not in buscar_pedido(1, email)