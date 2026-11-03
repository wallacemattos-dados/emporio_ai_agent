import uuid

import streamlit as st

from app.agent.graph import responder

st.set_page_config(page_title="Empório da Música", page_icon="🎸")
st.title("🎸 Empório da Música")
st.caption("Assistente virtual: instrumentos, preços, pedidos e políticas da loja.")


def nova_conversa() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.mensagens = []


def exibir(papel: str, texto: str) -> None:
    with st.chat_message(papel):
        st.markdown(texto.replace("$", r"\$"))


if "thread_id" not in st.session_state:
    nova_conversa()

with st.sidebar:
    st.button("Nova conversa", on_click=nova_conversa)

for mensagem in st.session_state.mensagens:
    exibir(mensagem["papel"], mensagem["texto"])

if pergunta := st.chat_input("Digite sua mensagem..."):
    st.session_state.mensagens.append({"papel": "user", "texto": pergunta})
    exibir("user", pergunta)
    with st.spinner("Consultando..."):
        resposta = responder(pergunta, st.session_state.thread_id)
    st.session_state.mensagens.append({"papel": "assistant", "texto": resposta})
    exibir("assistant", resposta)