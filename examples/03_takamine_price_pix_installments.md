# Example 3: Price, PIX discount and instalments (data + policy)

**Scenario:** The customer asks the price of the Takamine GD20, then the PIX price, then 12 instalments.

**Expected behaviour:** List price R$ 2,199.00 (the 12% promotion in the data is inactive and must not be applied); PIX price R$ 2,089.05 (5% off); 12 interest-free instalments of R$ 183.25, above the R$ 100 minimum instalment.

**Model configured:** `gemini-3.5-flash-lite` | **Generated:** 2026-11-04 by `gerar_exemplos.py` (real model calls; answers copied verbatim, not edited)

---

**Customer:** Quanto custa o Takamine GD20?

**Assistant:**

> O Takamine GD20 Dreadnought Natural custa R$ 2.199,00, mas sai por R$ 2.089,05 à vista no PIX, bicho! E ele está disponível aqui na loja. Quer garantir o seu?

*Tools used: consultar_banco_dados_loja | 4.0s*

**Customer:** E no PIX?

**Assistant:**

> O valor à vista no PIX para o Takamine GD20 é R$ 2.089,05, bicho! Posso separar um para você?

*Tools used: none | 2.1s*

**Customer:** E se eu parcelar em 12x?

**Assistant:**

> Aqui na Empório a gente parcela em até 12x sem juros no cartão de crédito, desde que cada parcela seja de pelo menos R$ 100,00, bicho! Como o Takamine GD20 custa R$ 2.199,00, dá para dividir em 12x de R$ 183,25 sem acréscimo. Quer fechar?

*Tools used: consultar_politicas_loja | 6.6s*
