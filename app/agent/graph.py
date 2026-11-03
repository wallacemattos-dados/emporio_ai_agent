import logging
import sqlite3
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.persona import montar_prompt_sistema
from app.agent.state import AgentState
from app.core.config import get_settings
from app.tools.csv_analyzer import consultar_banco_dados_loja, consultar_status_pedido
from app.tools.rag_policy import consultar_politicas_loja

logger = logging.getLogger(__name__)

TOOLS = [consultar_banco_dados_loja, consultar_status_pedido, consultar_politicas_loja]
LIMITE_DE_PASSOS = 12
MSG_ERRO = (
    "Desculpa, bicho, tive um problema aqui para consultar isso agora. "
    "Pode tentar de novo em instantes? Se preferir, fale com a equipe no (67) 3341-4444."
)


def criar_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(model=settings.llm_model, api_key=settings.google_api_key)


def criar_checkpointer() -> SqliteSaver:
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(settings.storage_dir / "checkpoints.sqlite", check_same_thread=False)
    return SqliteSaver(conexao)


def build_graph(llm=None, checkpointer=None):
    llm_com_tools = (llm or criar_llm()).bind_tools(TOOLS)

    def agent_llm(state: AgentState) -> dict:
        mensagens = [SystemMessage(montar_prompt_sistema()), *state["messages"]]
        return {"messages": [llm_com_tools.invoke(mensagens)]}

    grafo = StateGraph(AgentState)
    grafo.add_node("agent_llm", agent_llm)
    grafo.add_node("execute_tools", ToolNode(TOOLS))
    grafo.add_edge(START, "agent_llm")
    grafo.add_conditional_edges(
        "agent_llm", tools_condition, {"tools": "execute_tools", END: END}
    )
    grafo.add_edge("execute_tools", "agent_llm")
    return grafo.compile(checkpointer=checkpointer)


@lru_cache
def obter_grafo():
    return build_graph(checkpointer=criar_checkpointer())


def responder(mensagem: str, thread_id: str, grafo=None) -> str:
    grafo = grafo or obter_grafo()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": LIMITE_DE_PASSOS}
    try:
        resultado = grafo.invoke({"messages": [HumanMessage(mensagem)]}, config)
    except GraphRecursionError:
        logger.warning("Limite de passos atingido (thread %s)", thread_id)
        return MSG_ERRO
    except Exception:
        logger.exception("Falha ao processar a mensagem (thread %s)", thread_id)
        return MSG_ERRO
    texto = str(resultado["messages"][-1].text).strip()
    return texto or MSG_ERRO