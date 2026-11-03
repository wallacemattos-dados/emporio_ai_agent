from typing import Annotated, Literal, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

Intent = Literal[
    "chitchat",
    "loja_faq",
    "consulta_estoque_preco",
    "consulta_pedido",
    "out_of_scope",
]


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: NotRequired[Intent]