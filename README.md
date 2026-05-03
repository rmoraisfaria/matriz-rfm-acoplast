# Dashboard RFM B2B - Gestão de Contas

Aplicação local para análise de vendas, segmentação de clientes via matriz RFM (Recency, Frequency, Monetary) e gestão ativa de carteira B2B.

## Funcionalidades
- **Visão Executiva:** Resumo em tempo real da carteira (KPIs).
- **Matriz RFM:** Segmentação detalhada dos clientes com gráficos interativos.
- **Gestão de Contas:** Tabela acionável com sugestões de contato e prioridades.
- **Unificação de Clientes:** Lógica inteligente para agrupar clientes por Grupo Econômico, Raiz CNPJ ou manualmente, evitando duplicações no cálculo RFM.
- **Produtos:** Entendimento do mix por cliente e perfil de conta.

## Como Instalar

1. Certifique-se de ter o Python 3.9+ instalado.
2. Na pasta do projeto, crie um ambiente virtual (recomendado):
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Mac/Linux:
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Como Usar

1. Coloque o seu arquivo de vendas (ex: `Relatório Vendas 2025.csv`) dentro da pasta `/data`. O arquivo deve ter separador `;` e estar codificado preferencialmente em UTF-8-SIG (o padrão para exportações).
2. Execute o aplicativo:
   ```bash
   streamlit run app.py
   ```
3. O painel abrirá automaticamente no seu navegador.
4. (Opcional) Você pode colocar um arquivo `account_mapping.csv` na pasta raiz ou em `/data` se desejar forçar mapeamentos de conta.

## Decisões de Negócio
- A **Frequência (F)** do modelo RFM é contada com base em "Pedidos Únicos" (`N. Pedido`), evitando que a presença de vários itens infle artificialmente a frequência do cliente.
- O **Valor (M)** é calculado com base no `Vlr Total Item` sobre as linhas válidas de venda.
- Foram adotados 9 segmentos RFM padrões do varejo e B2B (ex: Campeões, Em Risco, Hibernando), mas os limites R-F-M são calculados por quintis com base nos dados reais ou configuráveis na aba Configurações.
- Grupos genéricos ("Grupo Revendas", "CLIENTES NACIONAIS") não são unificados automaticamente.
