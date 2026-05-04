# Documentação da Lógica RFM — Dashboard Acoplast

## 1. O que é RFM

RFM é um modelo de segmentação de clientes baseado em **três dimensões comportamentais**:

| Dimensão | Significado | Pergunta que responde |
|---|---|---|
| **R** — Recência | Há quantos **dias** o cliente fez a última compra | "Quando foi a última vez que comprou?" |
| **F** — Frequência | Quantos **pedidos únicos** o cliente fez no período | "Com que frequência compra?" |
| **M** — Monetário | Qual o **valor total** gasto pelo cliente no período | "Quanto gasta conosco?" |

Clientes com R alto (comprou recentemente), F alto (compra frequentemente) e M alto (gasta muito) são os melhores clientes. O modelo RFM permite classificar toda a carteira em segmentos acionáveis.

---

## 2. Como calculamos os Scores (1 a 5)

### Método: Quintis (pd.qcut)

Cada dimensão é dividida em **5 faixas de tamanho igual** (quintis), usando a distribuição real dos dados da carteira. Isso significa que ~20% dos clientes ficam em cada score.

| Score | Recência (R) | Frequência (F) | Monetário (M) |
|---|---|---|---|
| **5** (melhor) | Menores dias (comprou há pouco) | Mais pedidos | Maior valor gasto |
| **4** | | | |
| **3** | | | |
| **2** | | | |
| **1** (pior) | Mais dias (faz tempo que não compra) | Menos pedidos | Menor valor gasto |

> **Nota:** **Recência é invertida**: quanto MENOR o número de dias, MELHOR o score (5). Frequência e Monetário são diretos: quanto MAIOR, melhor o score.

### Tratamento de empates

Quando muitos clientes têm o mesmo valor (ex: muitos com 1 pedido), o `qcut` não consegue criar 5 faixas distintas. Nesses casos, usamos `rank(method='first')` como fallback para forçar a separação.

---

## 3. Regras de Segmentação — Mapeamento atual

Cada cliente recebe um score de 1-5 para R, F e M, gerando uma combinação como "5-4-3". Essas 125 combinações possíveis são agrupadas em **9 segmentos**:

### Tabela de Regras (ordem de prioridade)

As regras são avaliadas **na ordem abaixo** — a primeira que satisfizer é aplicada:

| # | Segmento | Regra (R, F, M) | Lógica |
|---|---|---|---|
| 1 | **Campeões** 🏆 | R≥4 **E** F≥4 **E** M≥4 | Comprou recentemente, frequentemente e gasta muito |
| 2 | **Grandes contas ativas** ⭐ | R≥4 **E** M≥4 (F qualquer) | Comprou recentemente e gasta muito, mas F pode ser moderada |
| 3 | **Contas estratégicas em risco** 🔥 | R≤2 **E** M≥4 | Gasta muito, mas faz tempo que não compra — ALERTA |
| 4 | **Contas frequentes de baixo valor** 🔄 | F≥4 **E** M≤2 | Compra frequentemente mas gasta pouco |
| 5 | **Oportunidade de expansão** 📈 | R≥3 **E** F≥3 **E** 2≤M≤3 | Ativo e frequente, com potencial de aumentar ticket |
| 6 | **Recém compradores** 🆕 | R≥4 **E** F≤2 | Comprou recentemente, mas fez poucos pedidos (conta nova) |
| 7 | **Hibernando** ❄️ | R≤2 **E** F≤2 | Faz tempo que não compra e fez poucos pedidos |
| 8 | **Inativos ou quase perdidos** ⚰️ | R=1 | Score de recência mínimo (mais distantes) |
| 9 | **Manutenção** 🔧 | Nenhuma acima | Tudo que não se encaixou nas regras anteriores |

---

## 4. Análise Crítica — Pontos de Atenção

Após pesquisa profunda sobre melhores práticas RFM (especialmente para B2B industrial), identifiquei os seguintes pontos na implementação atual:

### ✅ O que está correto

1. **Uso de quintis (qcut)** — Método padrão da indústria para distribuir scores proporcionalmente.
2. **Tratamento de empates** — Fallback com `rank(method='first')` evita crashes.
3. **Score R invertido** — Corretamente mapeia menos dias → score mais alto.
4. **Segmentos acionáveis** — Cada segmento tem ação sugerida clara.
5. **Unificação de contas** — Agrupamento por grupo econômico/CNPJ evita fragmentação da análise.

### ⚠️ Pontos que merecem revisão

#### Ponto 1: Conflito de prioridade entre regras 3 e 8
Um cliente com R=1 e M=5 (gasta muito mas sumiu há muito tempo) cai em "Contas estratégicas em risco" e não em "Inativos". Isso está correto no contexto B2B (prioriza clientes de alto valor que precisam ser resgatados).

#### Ponto 2: "Oportunidade de expansão" é restrita demais
A regra atual exige R≥3 **E** F≥3 **E** 2≤M≤3. Isso exclui contas com M=4 que poderiam subir para Campeões. Considerar ampliar para incluir M=3-4.

#### Ponto 3: "Manutenção" é ampla demais
O segmento catch-all "Manutenção" captura muitas combinações intermediárias. Pode ser útil dividir em "Manutenção ativa" (R≥3) e "Manutenção passiva" (R<3).

#### Ponto 4: Frequência em B2B industrial
Na Acoplast, a frequência de compra é naturalmente **baixa**. Um cliente que compra 2-3x por ano pode ser excelente. O quintil de frequência pode penalizar injustamente esses clientes. Considerar ajustar os limites manualmente no futuro.

---

## 5. Ações Sugeridas por Segmento

| Segmento | Prioridade | Ação Recomendada | Cadência |
|---|---|---|---|
| **Campeões** | Alta | Blindar relacionamento, cross-sell, pedir indicação | Quinzenal |
| **Grandes contas ativas** | Alta | Expandir mix de produtos, revisar histórico | Mensal |
| **Contas estratégicas em risco** | Alta | Contato consultivo urgente, entender queda | Semanal |
| **Oportunidade de expansão** | Média | Plano de crescimento, produtos complementares | Mensal |
| **Recém compradores** | Média | Pós-venda, criar próxima oportunidade | Mensal |
| **Freq. baixo valor** | Média | Aumentar ticket, sugerir pacote mínimo | Bimestral |
| **Hibernando** | Baixa/Média | Campanha de reativação | Trimestral |
| **Inativos/quase perdidos** | Baixa | Reativação estruturada ou repasse de carteira | Semestral |
| **Manutenção** | Baixa | Acompanhamento sob demanda | Mensal |

---

## 6. Decisões para validação

Revise os pontos abaixo e me diga se quer que eu ajuste algum:

1. **A ordem de prioridade das regras** está adequada ao contexto Acoplast?
2. **O segmento "Manutenção"** deveria ser dividido em sub-categorias?
3. **A frequência** deveria ter breakpoints customizados para o setor industrial (ex: 1 pedido = baixo, 2-3 = médio, 4+ = alto)?
4. **Peso diferenciado**: Quer que M (monetário) tenha mais peso na classificação final do que R e F?
