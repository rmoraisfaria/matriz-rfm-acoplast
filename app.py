import streamlit as st
import plotly.express as px
import pandas as pd
import os
import datetime
from data_processing import (
    load_data, clean_data, create_normalization_columns, create_account_key,
    calculate_rfm, classify_rfm_segment, generate_account_actions,
    format_currency, generate_merge_suggestions, calculate_migration
)
from ui_components import (
    create_kpi_card, plot_receita_mensal, plot_segment_distribution,
    plot_rfm_scatter, plot_rfm_heatmap, plot_rfm_treemap,
    plot_familia_produto, plot_grupo_receita,
    render_rfm_grid, render_segment_drilldown, render_migration_table
)

# Configuração da página
st.set_page_config(page_title="Acoplast - Gestão RFM", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS ---
st.markdown("""
<style>
    .css-18e3th9 { padding-top: 1rem; }
    .css-1d391kg { padding-top: 1rem; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
    .reportview-container .main .block-container{ max-width: 95%; }
</style>
""", unsafe_allow_html=True)

# --- AUTENTICAÇÃO ---
APP_PASSWORD = "Acoplast123"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("""
        <div style="text-align: center; padding: 60px 0 30px 0;">
            <h1 style="font-size: 42px; margin-bottom: 5px;">📊 Acoplast</h1>
            <p style="font-size: 18px; opacity: 0.7;">Gestão RFM — Dashboard Comercial</p>
        </div>
        """, unsafe_allow_html=True)
        senha = st.text_input("🔒 Digite a senha de acesso:", type="password", placeholder="Senha")
        if st.button("Entrar", use_container_width=True, type="primary"):
            if senha == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")
        st.markdown("<p style='text-align:center; opacity:0.4; font-size:12px; margin-top:40px;'>© Acoplast — Acesso restrito</p>", unsafe_allow_html=True)
    st.stop()

# --- CACHE E CARREGAMENTO ---
@st.cache_data(show_spinner="Carregando dados...")
def load_and_prep_data():
    # Priorizar o novo relatório 2025-2026
    candidates = [
        'data/Relatório de Vendas 2025-2026.csv',
        'Relatório de Vendas 2025-2026.csv',
        'data/Relatório Vendas 2025.csv',
        'Relatório Vendas 2025.csv',
    ]
    csv_path = None
    for path in candidates:
        if os.path.exists(path):
            csv_path = path
            break

    if csv_path is None:
        return None, None

    df_raw = load_data(csv_path)
    df_clean = clean_data(df_raw)
    df_norm = create_normalization_columns(df_clean)
    return df_norm, os.path.basename(csv_path)

df_base, loaded_file = load_and_prep_data()

if df_base is None:
    st.error("Nenhum arquivo de relatório encontrado na pasta 'data' ou na raiz.")
    st.stop()

# --- SIDEBAR CONFIGURAÇÕES ---
st.sidebar.title("⚙️ Configurações e Filtros")
st.sidebar.caption(f"📁 Arquivo: {loaded_file}")

# Configuração de Chave
st.sidebar.subheader("Estratégia de Unificação")
strat_options = ['Sugerida', 'Grupo Econômico', 'Raiz CNPJ', 'CNPJ Individual', 'Unidade']
selected_strat = st.sidebar.selectbox("Agrupar contas por:", strat_options, index=0)

@st.cache_data(show_spinner="Agrupando contas...")
def apply_account_key(df, strat):
    return create_account_key(df.copy(), strat)

df = apply_account_key(df_base, selected_strat)

# Filtros Globais
st.sidebar.subheader("Filtros Globais")

# Data
date_col_rfm = st.sidebar.selectbox("Data de referência para RFM:", ['data_pedido', 'data_faturamento'])
min_date = df[date_col_rfm].min()
max_date = df[date_col_rfm].max()

if pd.isna(min_date) or pd.isna(max_date):
    min_date, max_date = datetime.date(2025, 1, 1), datetime.date.today()

dates = st.sidebar.date_input("Período analisado", [min_date, max_date], min_value=min_date, max_value=max_date)

# Status
all_statuses = df['status_pedido'].unique().tolist()
default_statuses = [s for s in all_statuses if s in ['Faturado', 'Parcialmente faturado', 'Atendido']]
selected_statuses = st.sidebar.multiselect("Status do Pedido", all_statuses, default=default_statuses)

# Grupo Econômico
all_grupos = sorted([g for g in df['grupo_economico'].unique() if g and g != 'Sem Grupo'])
selected_grupos = st.sidebar.multiselect("Grupo Econômico", all_grupos)

# Família de Produto
all_familias = sorted([f for f in df['familia_produto'].unique() if f and f != 'Sem Família'])
selected_familias = st.sidebar.multiselect("Família de Produto", all_familias)

# Vendedores e UF
selected_vendedores = st.sidebar.multiselect("Vendedores", sorted(df['vendedor'].unique()))
selected_ufs = st.sidebar.multiselect("UF", sorted(df['uf'].unique()))

# Filtrar DataFrame Base
mask = (df['status_pedido'].isin(selected_statuses))
if len(dates) == 2:
    mask = mask & (df[date_col_rfm].dt.date >= dates[0]) & (df[date_col_rfm].dt.date <= dates[1])
if selected_grupos:
    mask = mask & (df['grupo_economico'].isin(selected_grupos))
if selected_familias:
    mask = mask & (df['familia_produto'].isin(selected_familias))
if selected_vendedores:
    mask = mask & (df['vendedor'].isin(selected_vendedores))
if selected_ufs:
    mask = mask & (df['uf'].isin(selected_ufs))

df_filtered = df[mask].copy()

# Base RFM Reference Date
st.sidebar.subheader("Data Base RFM")
ref_date_option = st.sidebar.radio("Calcular recência usando:", ["Data Máxima Filtrada", "Hoje"])
if ref_date_option == "Hoje":
    ref_date = pd.to_datetime('today')
else:
    if df_filtered.empty or pd.isna(df_filtered[date_col_rfm].max()):
        ref_date = pd.to_datetime('today')
    else:
        ref_date = df_filtered[date_col_rfm].max() + pd.Timedelta(days=1)

# Calcular RFM
@st.cache_data(show_spinner="Calculando Matriz RFM...")
def get_rfm_data(df_in, r_date, col_date, statuses):
    rfm = calculate_rfm(df_in, r_date, col_date, statuses)
    if not rfm.empty:
        rfm = classify_rfm_segment(rfm)
        rfm = generate_account_actions(rfm)
    return rfm

df_rfm = get_rfm_data(df_filtered, ref_date, date_col_rfm, selected_statuses)

# --- NAVEGAÇÃO ---
pages = ["Visão Executiva", "Matriz RFM", "Gestão de Contas", "Análise por Grupo", "Produtos e Famílias", "Unificação de Clientes"]
selected_page = st.sidebar.radio("Navegação", pages)

# ================================================================
# PÁGINA: VISÃO EXECUTIVA
# ================================================================
if selected_page == "Visão Executiva":
    st.title("📈 Visão Executiva")

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    receita_total = df_base[df_base['status_pedido'].isin(['Faturado', 'Parcialmente faturado', 'Atendido'])]['valor_item'].sum()
    receita_filtrada = df_filtered['valor_item'].sum()
    pendente = df_base[df_base['status_pedido'].str.contains('Pendente', case=False, na=False)]['valor_item'].sum()

    with col1:
        create_kpi_card("Receita Realizada (Filtro)", format_currency(receita_filtrada), f"Base Total: {format_currency(receita_total)}")
    with col2:
        create_kpi_card("Receita Pendente", format_currency(pendente))
    with col3:
        create_kpi_card("Contas Únicas", len(df_rfm))
    with col4:
        pedidos = df_filtered['pedido_id'].nunique()
        ticket = receita_filtrada / pedidos if pedidos > 0 else 0
        create_kpi_card("Ticket Médio (Pedido)", format_currency(ticket), f"Total Pedidos: {pedidos}")

    # Alertas Rápidos
    if not df_rfm.empty:
        risco = len(df_rfm[df_rfm['segmento_rfm'] == 'Contas estratégicas em risco'])
        inativos = len(df_rfm[df_rfm['dias_desde_ultima_compra'] > 90])
        st.warning(f"⚠️ Atenção: Temos **{risco}** contas estratégicas em risco e **{inativos}** contas sem comprar há mais de 90 dias.")

    # Gráficos
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(plot_receita_mensal(df_filtered, date_col_rfm), use_container_width=True)
    with col2:
        st.plotly_chart(plot_segment_distribution(df_rfm), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        vend_df = df_filtered.groupby('vendedor')['valor_item'].sum().reset_index().sort_values('valor_item', ascending=True).tail(10)
        fig_v = px.bar(vend_df, x='valor_item', y='vendedor', orientation='h', title='Top 10 Vendedores')
        fig_v.update_xaxes(tickprefix="R$ ")
        st.plotly_chart(fig_v, use_container_width=True)
    with col2:
        if not df_rfm.empty:
            acc_df = df_rfm.sort_values('valor_total', ascending=True).tail(10)
            fig_a = px.bar(acc_df, x='valor_total', y='account_name', orientation='h', title='Top 10 Contas (Receita)')
            fig_a.update_xaxes(tickprefix="R$ ")
            st.plotly_chart(fig_a, use_container_width=True)

# ================================================================
# PÁGINA: MATRIZ RFM
# ================================================================
elif selected_page == "Matriz RFM":
    st.title("🎯 Matriz RFM")

    if df_rfm.empty:
        st.info("Nenhuma conta encontrada com os filtros atuais.")
    else:
        tab_grade, tab_migracao, tab_analise = st.tabs(["📊 Grade RFM", "🔄 Migração", "📈 Análise"])

        # --- TAB: GRADE RFM ---
        with tab_grade:
            st.markdown("### Grade de Segmentos RFM")
            st.markdown("Cada bloco representa um segmento. **Clique no seletor abaixo** para ver as empresas de cada segmento.")
            render_rfm_grid(df_rfm)

            st.markdown("---")
            st.markdown("### 🔍 Detalhar Segmento")
            render_segment_drilldown(df_rfm)

        # --- TAB: MIGRAÇÃO ---
        with tab_migracao:
            st.markdown("### Tabela de Migração")
            st.markdown("A tabela indica o fluxo migratório de contas entre segmentos RFM. "
                        "Os cards em destaque indicam a **maior migração** de cada linha.")

            # Date range for migration periods
            data_min = df_filtered[date_col_rfm].min()
            data_max = df_filtered[date_col_rfm].max()

            if pd.notna(data_min) and pd.notna(data_max):
                midpoint = data_min + (data_max - data_min) / 2

                st.info(f"💡 **Período recomendado**: Anterior = {data_min.strftime('%d/%m/%Y')} a {midpoint.strftime('%d/%m/%Y')} | "
                        f"Atual = {(midpoint + pd.Timedelta(days=1)).strftime('%d/%m/%Y')} a {data_max.strftime('%d/%m/%Y')}")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Período Anterior**")
                    pa = st.date_input("Início / Fim", [data_min.date(), midpoint.date()],
                                       min_value=data_min.date(), max_value=data_max.date(), key='mig_pa')
                with col_b:
                    st.markdown("**Período Atual**")
                    pb = st.date_input("Início / Fim", [(midpoint + pd.Timedelta(days=1)).date(), data_max.date()],
                                       min_value=data_min.date(), max_value=data_max.date(), key='mig_pb')

                if len(pa) == 2 and len(pb) == 2:
                    with st.spinner("Calculando migração..."):
                        cross, merged = calculate_migration(df_filtered, date_col_rfm, selected_statuses,
                                                            pa[0], pa[1], pb[0], pb[1])
                    if not cross.empty:
                        render_migration_table(cross, merged)
                    else:
                        st.warning("Sem dados suficientes em um dos períodos para calcular a migração.")
                else:
                    st.warning("Selecione início e fim para ambos os períodos.")
            else:
                st.warning("Sem dados de datas para calcular migração.")

        # --- TAB: ANÁLISE ---
        with tab_analise:
            st.markdown("### Dispersão RFM")
            st.markdown("Eixo X = **Recência** (dias), Eixo Y = **Valor** (log). Bolha = **Frequência**.")
            st.plotly_chart(plot_rfm_scatter(df_rfm), use_container_width=True)

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(plot_rfm_heatmap(df_rfm), use_container_width=True)
            with col2:
                st.plotly_chart(plot_rfm_treemap(df_rfm), use_container_width=True)

            st.markdown("---")
            st.subheader("Base Completa de Clientes RFM")
            seg_filtro = st.multiselect("Filtrar Segmento:", sorted(df_rfm['segmento_rfm'].unique()))
            df_show = df_rfm.copy()
            if seg_filtro:
                df_show = df_show[df_show['segmento_rfm'].isin(seg_filtro)]

            cols_to_show = ['account_name', 'grupo_economico', 'segmento_rfm', 'RFM_score', 'valor_total',
                            'pedidos_unicos', 'dias_desde_ultima_compra', 'vendedor_principal',
                            'familia_principal', 'qtde_unidades']
            available_cols = [c for c in cols_to_show if c in df_show.columns]
            st.dataframe(df_show[available_cols].style.format({'valor_total': 'R$ {:,.2f}'}), use_container_width=True)

# ================================================================
# PÁGINA: GESTÃO DE CONTAS
# ================================================================
elif selected_page == "Gestão de Contas":
    st.title("💼 Gestão Ativa de Contas")

    if df_rfm.empty:
        st.info("Sem dados.")
    else:
        st.markdown("Acompanhe e atue de forma proativa na sua carteira de clientes com base no modelo RFM.")
        st.info("**Alta Prioridade**: Contas vitais que requerem contato urgente.\n\n**Contas em Risco**: Clientes com gasto alto que pararam de comprar.")

        col1, col2, col3, col4 = st.columns(4)
        show_alta = col1.checkbox("Apenas Alta Prioridade", value=False)
        show_risco = col2.checkbox("Contas em Risco", value=False)
        show_mais_90 = col3.checkbox("Sem compra > 90 dias", value=False)

        df_gestao = df_rfm.copy()
        if show_alta:
            df_gestao = df_gestao[df_gestao['prioridade_gestao'] == 'Alta']
        if show_risco:
            df_gestao = df_gestao[df_gestao['segmento_rfm'] == 'Contas estratégicas em risco']
        if show_mais_90:
            df_gestao = df_gestao[df_gestao['dias_desde_ultima_compra'] > 90]

        cols_gestao = ['account_name', 'grupo_economico', 'prioridade_gestao', 'segmento_rfm',
                       'proxima_acao_sugerida', 'prazo_sugerido_contato', 'dias_desde_ultima_compra',
                       'valor_total', 'vendedor_responsavel']
        available_cols = [c for c in cols_gestao if c in df_gestao.columns]
        st.dataframe(
            df_gestao[available_cols].sort_values(['prioridade_gestao', 'dias_desde_ultima_compra'], ascending=[True, False])
            .style.format({'valor_total': 'R$ {:,.2f}'}),
            use_container_width=True
        )

        st.download_button(
            label="📥 Exportar Lista de Gestão (CSV)",
            data=df_gestao.to_csv(sep=';', index=False, decimal=','),
            file_name="gestao_contas_acoplast.csv",
            mime="text/csv"
        )

# ================================================================
# PÁGINA: ANÁLISE POR GRUPO
# ================================================================
elif selected_page == "Análise por Grupo":
    st.title("🏢 Análise por Grupo Econômico")
    st.markdown("Selecione um grupo para ver a Matriz RFM das **unidades individuais** dentro dele.")

    # Listar apenas grupos com dados significativos
    grupos_disponiveis = sorted([g for g in df_filtered['grupo_economico'].unique()
                                  if g and g != 'Sem Grupo' and g != 'Clientes Nacionais'])

    if not grupos_disponiveis:
        st.info("Nenhum grupo econômico disponível com os filtros atuais.")
    else:
        selected_grupo = st.selectbox("Selecione o Grupo Econômico:", [""] + grupos_disponiveis)

        if selected_grupo:
            # Filtrar dados do grupo
            df_grupo = df_filtered[df_filtered['grupo_economico'] == selected_grupo].copy()

            if df_grupo.empty:
                st.warning("Nenhum dado encontrado para este grupo.")
            else:
                # Para a análise intra-grupo, forçar agrupamento por CNPJ Individual
                df_grupo_keyed = create_account_key(
                    create_normalization_columns(df_grupo.copy()),
                    'CNPJ Individual'
                )

                # Calcular RFM intra-grupo
                rfm_grupo = calculate_rfm(df_grupo_keyed, ref_date, date_col_rfm, selected_statuses)

                # KPIs do Grupo
                col1, col2, col3, col4 = st.columns(4)
                receita_grupo = df_grupo['valor_item'].sum()
                with col1:
                    create_kpi_card("Receita do Grupo", format_currency(receita_grupo))
                with col2:
                    create_kpi_card("Unidades / CNPJs", df_grupo['CNPJ'].nunique() if 'CNPJ' in df_grupo.columns else '—')
                with col3:
                    pedidos_g = df_grupo['pedido_id'].nunique()
                    create_kpi_card("Pedidos", pedidos_g)
                with col4:
                    ticket_g = receita_grupo / pedidos_g if pedidos_g > 0 else 0
                    create_kpi_card("Ticket Médio", format_currency(ticket_g))

                st.markdown("---")

                if not rfm_grupo.empty and len(rfm_grupo) >= 4:
                    rfm_grupo = classify_rfm_segment(rfm_grupo)
                    rfm_grupo = generate_account_actions(rfm_grupo)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.plotly_chart(plot_rfm_scatter(rfm_grupo), use_container_width=True)
                    with col2:
                        st.plotly_chart(plot_segment_distribution(rfm_grupo), use_container_width=True)

                    st.subheader("Contas do Grupo")
                    cols_grupo = ['account_name', 'segmento_rfm', 'RFM_score', 'valor_total',
                                  'pedidos_unicos', 'dias_desde_ultima_compra', 'vendedor_principal']
                    available = [c for c in cols_grupo if c in rfm_grupo.columns]
                    st.dataframe(rfm_grupo[available].sort_values('valor_total', ascending=False)
                                 .style.format({'valor_total': 'R$ {:,.2f}'}), use_container_width=True)
                elif not rfm_grupo.empty:
                    st.info("Grupo possui menos de 4 contas — segmentação RFM não é aplicável. Mostrando dados brutos.")
                    st.dataframe(rfm_grupo[['account_name', 'valor_total', 'pedidos_unicos', 'dias_desde_ultima_compra']]
                                 .sort_values('valor_total', ascending=False)
                                 .style.format({'valor_total': 'R$ {:,.2f}'}), use_container_width=True)
                else:
                    st.warning("Sem dados RFM para este grupo (verifique os filtros de status).")

                # Famílias de Produto dentro do grupo
                st.markdown("---")
                st.subheader("Mix de Famílias de Produto no Grupo")
                st.plotly_chart(plot_familia_produto(df_grupo, top_n=15), use_container_width=True)

        else:
            # Visão geral: ranking de grupos
            st.markdown("### Ranking dos Maiores Grupos por Receita")
            if not df_rfm.empty and 'grupo_economico' in df_rfm.columns:
                st.plotly_chart(plot_grupo_receita(df_rfm, top_n=20), use_container_width=True)

# ================================================================
# PÁGINA: PRODUTOS E FAMÍLIAS
# ================================================================
elif selected_page == "Produtos e Famílias":
    st.title("📦 Produtos e Famílias")

    # Análise por Família de Produto
    st.subheader("Receita por Família de Produto")
    st.markdown("Visão consolidada por **família de produto** — ideal para entender quais linhas geram mais resultado.")
    st.plotly_chart(plot_familia_produto(df_filtered, top_n=25), use_container_width=True)

    st.markdown("---")

    # Top produtos individuais
    st.subheader("Top 20 Produtos Individuais por Receita")
    prod_rev = df_filtered.groupby('produto')['valor_item'].sum().reset_index().sort_values('valor_item', ascending=False).head(20)
    fig_p = px.bar(prod_rev.sort_values('valor_item', ascending=True), x='valor_item', y='produto', orientation='h',
                   title='Top 20 Produtos por Receita',
                   color_discrete_sequence=['#00897B'])
    fig_p.update_xaxes(tickprefix="R$ ")
    st.plotly_chart(fig_p, use_container_width=True)

    st.markdown("---")

    # Histórico por Conta
    st.subheader("Busca de Histórico por Conta")
    contas_list = sorted(df_filtered['account_name'].unique())
    selected_acc = st.selectbox("Selecione uma conta para ver o histórico de pedidos:", [""] + list(contas_list))

    if selected_acc:
        df_acc = df_filtered[df_filtered['account_name'] == selected_acc]
        hist_cols = ['pedido_id', 'data_pedido', 'status_pedido', 'familia_produto', 'produto',
                     'qtde_solic', 'valor_item', 'vendedor']
        available = [c for c in hist_cols if c in df_acc.columns]
        st.dataframe(df_acc[available].sort_values('data_pedido', ascending=False)
                     .style.format({'valor_item': 'R$ {:,.2f}'}), use_container_width=True)

# ================================================================
# PÁGINA: UNIFICAÇÃO DE CLIENTES
# ================================================================
elif selected_page == "Unificação de Clientes":
    st.title("🔗 Sugestões de Unificação")
    st.markdown("Identificação de clientes que provavelmente são a mesma conta, mas não foram agrupados pela estratégia atual.")

    with st.spinner("Analisando base para sugestões..."):
        sug_df = generate_merge_suggestions(df_filtered)

    if sug_df.empty:
        st.success("Não foram encontradas sugestões óbvias de unificação com os filtros atuais.")
    else:
        st.warning(f"Encontramos {len(sug_df)} contas com potencial para unificação.")
        st.dataframe(sug_df.style.format({'valor_total': 'R$ {:,.2f}'}), use_container_width=True)

        st.info("Para forçar a união, crie um arquivo `account_mapping.csv` na pasta `/data` com as colunas: "
                "`source_type, source_value, account_key_final, account_name_final` e reinicie a aplicação.")
