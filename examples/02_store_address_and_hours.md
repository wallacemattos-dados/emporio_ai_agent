# Example 2: General store information (policies via RAG)

**Scenario:** The customer asks for the address and the opening hours.

**Expected behaviour:** Rua 14 de Maio, 3200, Centro, Campo Grande - MS. Monday to Friday 09:00-18:00, Saturday 09:00-13:00, closed on Sundays and holidays.

**Model configured:** `gemini-3.5-flash-lite` | **Generated:** 2026-11-04 by `gerar_exemplos.py` (real model calls; answers copied verbatim, not edited)

---

**Customer:** Qual o endereço da loja?

**Assistant:**

> Estamos na Rua 14 de Maio, 3200 — Centro, aqui em Campo Grande (MS). Aparece por aqui para tomar um café e conferir nosso som!

*Tools used: consultar_politicas_loja | 4.2s*

**Customer:** E qual o horário de funcionamento?

**Assistant:**

> Funcionamos de segunda a sexta, das 09h às 18h, e aos sábados, das 09h às 13h. Aos domingos e feriados a loja fica fechada, bicho!

*Tools used: consultar_politicas_loja | 3.1s*
