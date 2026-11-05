# Example 4: Withdrawal right and order lookup (policy + real-time data)

**Scenario:** The customer regrets a purchase and wants to return it, then identifies the order.

**Expected behaviour:** Explains the 7-day right of withdrawal (original packaging, refund within 10 business days, return shipping paid by the store), asks when the item was received instead of assuming, and looks up order 1 (delivered) only after the order number and e-mail are given.

**Model configured:** `gemini-3.5-flash-lite` | **Generated:** 2026-11-04 by `gerar_exemplos.py` (real model calls; answers copied verbatim, not edited)

---

**Customer:** Me arrependi da minha compra, posso devolver meu pedido?

**Assistant:**

> Pode sim, bicho! O prazo para devolução por arrependimento é de até 7 dias corridos após o recebimento do produto. 
> 
> Me conta: quando foi que você recebeu o seu pedido? Assim já te explico os próximos passos!

*Tools used: none | 2.6s*

**Customer:** É o pedido 1 e meu e-mail é pedro.oliveira@jmail.com

**Assistant:**

> Vi aqui que o seu pedido do violão Martin D-28 foi entregue, Pedro! Como a política de devolução por arrependimento é de até 7 dias corridos após o recebimento, me confirma a data exata em que o instrumento chegou aí para sabermos se ainda estamos no prazo, beleza?

*Tools used: consultar_status_pedido | 6.6s*

**Customer:** Recebi há 3 dias. Como faço a devolução?

**Assistant:**

> Show de bola, você tá dentro do prazo dos 7 dias! 
> 
> Para seguir com a devolução, o instrumento precisa estar na embalagem original, sem sinais de uso e com todos os manuais, beleza? O frete de devolução é por nossa conta.
> 
> Como o pedido foi pago via PIX, o reembolso é feito na mesma forma de pagamento em até 10 dias úteis após o produto chegar aqui e passar pela nossa análise. Se quiser iniciar o processo, é só entrar em contato com a nossa equipe pelo e-mail contato@emporiodamusica.com.br ou pelo WhatsApp (67) 3341-4444.

*Tools used: consultar_politicas_loja | 7.4s*
