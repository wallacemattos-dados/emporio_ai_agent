# Example 1: Catalogue search with a price ceiling

**Scenario:** The customer asks which acoustic guitars (violões) are available for up to R$ 1,000.

**Expected behaviour:** Only models that are active and in stock, using the promotional price when a promotion is active. No unavailable model (e.g. the out-of-stock Giannini GF-3D) in the list.

**Model configured:** `gemini-3.5-flash-lite` | **Generated:** 2026-11-04 by `gerar_exemplos.py` (real model calls; answers copied verbatim, not edited)

---

**Customer:** Quais opções de violões disponíveis custando até R$1000?

**Assistant:**

> Olha só, temos ótimas opções de violões até R$ 1.000 disponíveis por aqui, bicho:
> 
> - **Tagima Memphis AC-39 Nylon Natural**: R$ 429,90 (ou R$ 408,41 no PIX)
> - **Rozini RC-104 Nylon Estudante**: R$ 459,90 (ou R$ 436,91 no PIX)
> - **Shelby SN-100 Folk Aço Preto**: R$ 549,00 (ou R$ 521,55 no PIX)
> - **Giannini GF-1R Aço Folk Sunburst**: R$ 579,90 (ou R$ 550,91 no PIX)
> - **Yamaha C40 Nylon Natural**: R$ 599,00 (ou R$ 569,91 no PIX)
> 
> Algum desses faz seu estilo para garantir o som?

*Tools used: consultar_banco_dados_loja | 6.7s*
