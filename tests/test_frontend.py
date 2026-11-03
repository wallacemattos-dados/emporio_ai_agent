from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.agent import graph

FRONTEND = Path(__file__).resolve().parents[1] / "frontend.py"


def test_chat_exibe_pergunta_e_resposta_e_mantem_a_mesma_conversa(monkeypatch):
    recebidos = []

    def responder_falso(mensagem, thread_id):
        recebidos.append((mensagem, thread_id))
        return "Custa R$ 2.199,00 (ou R$ 2.089,05 no PIX)."

    monkeypatch.setattr(graph, "responder", responder_falso)

    app = AppTest.from_file(str(FRONTEND)).run()
    app.chat_input[0].set_value("Quanto custa o GD20?").run()
    app.chat_input[0].set_value("E no PIX?").run()

    assert not app.exception
    assert [m.markdown[0].value for m in app.chat_message if m.name == "user"] == [
        "Quanto custa o GD20?",
        "E no PIX?",
    ]
    assert recebidos[0][1] == recebidos[1][1]
    assert r"R\$ 2.199,00" in app.chat_message[1].markdown[0].value