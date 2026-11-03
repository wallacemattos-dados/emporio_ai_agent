import sqlite3

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from langgraph.types import RetryPolicy

from app.agent import graph as modulo_grafo
from app.agent.graph import MSG_ERRO, build_graph, responder


class LLMFalso:
    """Substitui o Gemini: devolve respostas roteirizadas e guarda o que recebeu."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.ferramentas = []

    def bind_tools(self, tools):
        self.ferramentas = [t.name for t in tools]
        return self

    def invoke(self, mensagens):
        self.chamadas.append(list(mensagens))
        return self.respostas.pop(0)


def chamada_gd20(id_chamada="call_1"):
    sql = "SELECT nome, preco_tabela_brl FROM catalogo WHERE nome ILIKE '%gd20%'"
    return AIMessage(
        content="",
        tool_calls=[{"name": "consultar_banco_dados_loja", "args": {"sql": sql}, "id": id_chamada}],
    )


def test_ciclo_agente_ferramenta_agente():
    llm = LLMFalso([chamada_gd20(), AIMessage("O Takamine GD20 custa R$ 2.199,00.")])
    grafo = build_graph(llm=llm, checkpointer=MemorySaver())

    texto = responder("Quanto custa o Takamine GD20?", "t1", grafo)

    assert texto == "O Takamine GD20 custa R$ 2.199,00."
    assert len(llm.chamadas) == 2
    resultado_da_tool = [m for m in llm.chamadas[1] if isinstance(m, ToolMessage)][0]
    assert "2199" in resultado_da_tool.content
    assert set(llm.ferramentas) == {
        "consultar_banco_dados_loja",
        "consultar_status_pedido",
        "consultar_politicas_loja",
    }


def test_prompt_do_sistema_vai_primeiro_mas_nao_e_salvo_no_historico():
    llm = LLMFalso([AIMessage("Oi!")])
    grafo = build_graph(llm=llm, checkpointer=MemorySaver())
    responder("Oi", "t1", grafo)

    assert isinstance(llm.chamadas[0][0], SystemMessage)
    salvas = grafo.get_state({"configurable": {"thread_id": "t1"}}).values["messages"]
    assert not any(isinstance(m, SystemMessage) for m in salvas)


def test_memoria_sobrevive_a_reinicio_e_nao_vaza_entre_conversas(tmp_path):
    caminho = tmp_path / "checkpoints.sqlite"

    def novo_grafo(llm):
        conexao = sqlite3.connect(caminho, check_same_thread=False)
        return build_graph(llm=llm, checkpointer=SqliteSaver(conexao))

    responder("Meu nome é Rafael", "conversa-a", novo_grafo(LLMFalso([AIMessage("Oi, Rafael!")])))

    llm_depois = LLMFalso([AIMessage("Lembro de você!"), AIMessage("Quem é você?")])
    grafo_depois = novo_grafo(llm_depois)
    responder("Você lembra de mim?", "conversa-a", grafo_depois)
    responder("Você lembra de mim?", "conversa-b", grafo_depois)

    historico_a = [m.content for m in llm_depois.chamadas[0]]
    historico_b = [m.content for m in llm_depois.chamadas[1]]
    assert "Meu nome é Rafael" in historico_a
    assert "Meu nome é Rafael" not in historico_b


def test_erro_inesperado_vira_mensagem_amigavel():
    class GrafoQuebrado:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("API fora do ar")

    assert responder("Oi", "t1", GrafoQuebrado()) == MSG_ERRO


def test_loop_infinito_de_ferramentas_e_interrompido():
    llm = LLMFalso([chamada_gd20() for _ in range(50)])
    grafo = build_graph(llm=llm, checkpointer=MemorySaver())

    assert responder("Quanto custa?", "t1", grafo) == MSG_ERRO
    assert len(llm.chamadas) < 50


class ErroDeApi(Exception):
    def __init__(self, codigo):
        super().__init__(f"{codigo} erro simulado")
        self.code = codigo


class LLMInstavel(LLMFalso):
    """Falha com o código HTTP indicado nas primeiras `falhas` tentativas."""

    def __init__(self, falhas, respostas, codigo=503):
        super().__init__(respostas)
        self.falhas = falhas
        self.codigo = codigo
        self.tentativas = 0

    def invoke(self, mensagens):
        self.tentativas += 1
        if self.tentativas <= self.falhas:
            raise ErroDeApi(self.codigo)
        return super().invoke(mensagens)


def retry_rapido(monkeypatch):
    monkeypatch.setattr(
        modulo_grafo,
        "POLITICA_DE_RETRY",
        RetryPolicy(initial_interval=0.01, max_attempts=3, retry_on=modulo_grafo.erro_transitorio),
    )


def test_erro_503_passageiro_e_repetido_ate_funcionar(monkeypatch):
    retry_rapido(monkeypatch)
    llm = LLMInstavel(falhas=2, respostas=[AIMessage("Oi!")])
    grafo = build_graph(llm=llm, checkpointer=MemorySaver())

    assert responder("Oi", "t1", grafo) == "Oi!"
    assert llm.tentativas == 3
    salvas = grafo.get_state({"configurable": {"thread_id": "t1"}}).values["messages"]
    assert [m.content for m in salvas].count("Oi") == 1


def test_503_persistente_desiste_apos_as_tentativas_e_devolve_mensagem_amigavel(monkeypatch):
    retry_rapido(monkeypatch)
    llm = LLMInstavel(falhas=99, respostas=[])
    grafo = build_graph(llm=llm, checkpointer=MemorySaver())

    assert responder("Oi", "t1", grafo) == MSG_ERRO
    assert llm.tentativas == 3


def test_erro_que_nao_e_passageiro_nao_e_repetido(monkeypatch):
    retry_rapido(monkeypatch)
    llm = LLMInstavel(falhas=99, respostas=[], codigo=400)
    grafo = build_graph(llm=llm, checkpointer=MemorySaver())

    assert responder("Oi", "t1", grafo) == MSG_ERRO
    assert llm.tentativas == 1