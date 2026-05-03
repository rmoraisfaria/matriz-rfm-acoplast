import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data_processing import format_currency

# ============================================================
# SEGMENT STYLING
# ============================================================

SEGMENT_STYLES = {
    'Campeões':                         {'bg': '#1B5E20', 'text': '#fff', 'icon': '🏆'},
    'Grandes contas ativas':            {'bg': '#2E7D32', 'text': '#fff', 'icon': '⭐'},
    'Contas estratégicas em risco':     {'bg': '#E65100', 'text': '#fff', 'icon': '🔥'},
    'Oportunidade de expansão':         {'bg': '#F9A825', 'text': '#1a1a1a', 'icon': '📈'},
    'Manutenção':                       {'bg': '#546E7A', 'text': '#fff', 'icon': '🔧'},
    'Inativos ou quase perdidos':       {'bg': '#3E2723', 'text': '#fff', 'icon': '⚰️'},
    'Recém compradores':                {'bg': '#00897B', 'text': '#fff', 'icon': '🆕'},
    'Contas frequentes de baixo valor': {'bg': '#1565C0', 'text': '#fff', 'icon': '🔄'},
    'Hibernando':                       {'bg': '#B71C1C', 'text': '#fff', 'icon': '❄️'},
}

# Grid layout: rows from high monetary (top) to low (bottom),
# columns from old recency (left) to recent (right)
SEGMENT_GRID = [
    ['Contas estratégicas em risco', 'Grandes contas ativas', 'Campeões'],
    ['Inativos ou quase perdidos', 'Manutenção', 'Oportunidade de expansão'],
    ['Hibernando', 'Contas frequentes de baixo valor', 'Recém compradores'],
]


# ============================================================
# KPI CARDS
# ============================================================

def create_kpi_card(title, value, subtitle=None, icon=None):
    """Renderiza um card KPI moderno."""
    st.markdown(f"""
        <div style="background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <p style="color: var(--text-color); opacity: 0.7; font-size: 14px; margin: 0; font-weight: 500;">{title}</p>
            <h2 style="color: var(--text-color); font-size: 28px; margin: 5px 0; font-weight: bold;">{value}</h2>
            {f'<p style="color: var(--text-color); opacity: 0.6; font-size: 12px; margin: 0;">{subtitle}</p>' if subtitle else ''}
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# RFM VISUAL GRID
# ============================================================

def render_rfm_grid(df_rfm):
    """Renders the RFM segment grid with colored cards and metrics."""
    if df_rfm.empty:
        st.info("Sem dados para exibir a grade RFM.")
        return

    # Pre-compute metrics per segment
    seg_metrics = {}
    for seg in df_rfm['segmento_rfm'].unique():
        subset = df_rfm[df_rfm['segmento_rfm'] == seg]
        seg_metrics[seg] = {
            'count': len(subset),
            'revenue': subset['valor_total'].sum(),
            'avg_recency': subset['dias_desde_ultima_compra'].mean(),
            'avg_frequency': subset['pedidos_unicos'].mean(),
            'avg_ticket': subset['ticket_medio_pedido'].mean() if 'ticket_medio_pedido' in subset.columns else 0,
        }

    # Summary panel + grid
    col_summary, col_grid = st.columns([1, 3])

    with col_summary:
        total = len(df_rfm)
        receita = df_rfm['valor_total'].sum()
        ticket = receita / total if total > 0 else 0
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 20px; border-radius: 16px; text-align: center; color: white; height: 100%;">
            <div style="font-size: 48px; font-weight: 800; line-height: 1;">{total}</div>
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 20px;">Total de Contas</div>
            <hr style="border: 1px solid rgba(255,255,255,0.3); margin: 15px 0;">
            <div style="font-size: 20px; font-weight: 700;">{format_currency(receita)}</div>
            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 12px;">Receita Total</div>
            <div style="font-size: 18px; font-weight: 600;">{format_currency(ticket)}</div>
            <div style="font-size: 12px; opacity: 0.8;">Ticket Médio</div>
        </div>
        """, unsafe_allow_html=True)

    with col_grid:
        # Axis labels
        st.markdown("""
        <div style="display: flex; justify-content: space-between; padding: 0 10px; margin-bottom: 4px;">
            <span style="font-size: 11px; color: #999;">← MAIS TEMPO SEM COMPRAR</span>
            <span style="font-size: 11px; color: #999;">COMPROU RECENTEMENTE →</span>
        </div>
        """, unsafe_allow_html=True)

        for row_idx, row_segments in enumerate(SEGMENT_GRID):
            cols = st.columns(len(row_segments))
            for col_idx, seg_name in enumerate(row_segments):
                with cols[col_idx]:
                    m = seg_metrics.get(seg_name, {'count': 0, 'revenue': 0, 'avg_recency': 0})
                    style = SEGMENT_STYLES.get(seg_name, {'bg': '#757575', 'text': '#fff', 'icon': '📊'})
                    st.markdown(f"""
                    <div style="background-color: {style['bg']}; color: {style['text']}; padding: 14px; border-radius: 10px; margin-bottom: 6px; min-height: 110px; position: relative;">
                        <div style="font-size: 13px; font-weight: 700; margin-bottom: 8px;">{style['icon']} {seg_name}</div>
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <div>
                                <span style="font-size: 22px; font-weight: 800;">{m['count']}</span>
                                <span style="font-size: 11px; opacity: 0.8;"> contas</span>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 13px; font-weight: 600;">{format_currency(m['revenue'])}</div>
                            </div>
                        </div>
                        <div style="font-size: 11px; opacity: 0.75; margin-top: 6px;">
                            Recência média: {m['avg_recency']:.0f} dias
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Y-axis label
        st.markdown("""
        <div style="display: flex; justify-content: space-between; padding: 0 10px; margin-top: 2px;">
            <span style="font-size: 11px; color: #999;">↑ ALTO VALOR</span>
            <span style="font-size: 11px; color: #999;">BAIXO VALOR ↓</span>
        </div>
        """, unsafe_allow_html=True)


def render_segment_drilldown(df_rfm):
    """Renders a drilldown selector and table for a chosen segment."""
    if df_rfm.empty:
        return

    segments = sorted(df_rfm['segmento_rfm'].unique())
    selected_seg = st.selectbox("🔍 Detalhar segmento:", ["Selecione um segmento..."] + segments, key='drilldown_seg')

    if selected_seg and selected_seg != "Selecione um segmento...":
        df_seg = df_rfm[df_rfm['segmento_rfm'] == selected_seg].copy()
        style = SEGMENT_STYLES.get(selected_seg, {'bg': '#757575', 'icon': '📊'})

        st.markdown(f"### {style['icon']} {selected_seg} — {len(df_seg)} contas")

        cols_show = ['account_name', 'grupo_economico', 'valor_total', 'pedidos_unicos',
                     'dias_desde_ultima_compra', 'vendedor_principal', 'familia_principal',
                     'proxima_acao_sugerida']
        available = [c for c in cols_show if c in df_seg.columns]
        st.dataframe(
            df_seg[available].sort_values('valor_total', ascending=False)
            .style.format({'valor_total': 'R$ {:,.2f}'}),
            use_container_width=True
        )
        st.download_button(
            f"📥 Exportar {selected_seg} (CSV)",
            df_seg[available].to_csv(sep=';', index=False, decimal=','),
            f"segmento_{selected_seg.replace(' ', '_')}.csv",
            "text/csv"
        )


# ============================================================
# MIGRATION TABLE
# ============================================================

def render_migration_table(cross_df, merged_df):
    """Renders a styled migration matrix table."""
    if cross_df.empty:
        st.info("Sem dados de migração para exibir.")
        return

    max_val = cross_df.drop('Total', axis=0, errors='ignore').drop('Total', axis=1, errors='ignore').max().max()
    if max_val == 0:
        max_val = 1

    # Build HTML table
    cols = [c for c in cross_df.columns]
    rows = [r for r in cross_df.index]

    html = '<div style="overflow-x: auto;">'
    html += '<table style="width:100%; border-collapse: collapse; font-size: 13px;">'

    # Header row
    html += '<tr><th style="padding:10px 8px; text-align:left; background:#f0f2f6; border:1px solid #ddd; font-size:11px; min-width:140px;">DO PERÍODO ANTERIOR →</th>'
    for col in cols:
        bg = '#e8eaf6' if col != 'Total' else '#c5cae9'
        html += f'<th style="padding:10px 6px; text-align:center; background:{bg}; border:1px solid #ddd; font-size:11px; min-width:80px;">{col}</th>'
    html += '</tr>'

    # Data rows
    for row_name in rows:
        is_total = row_name == 'Total'
        row_bg = '#f5f5f5' if is_total else '#fff'
        html += f'<tr>'
        # Row label
        label_style = f'background:{row_bg}; font-weight:{"700" if is_total else "600"}; border:1px solid #ddd; padding:8px;'
        html += f'<td style="{label_style}">{row_name}</td>'

        # Find max in this row (excluding Total) for highlighting
        row_data = cross_df.loc[row_name]
        row_vals = [row_data.get(c, 0) for c in cols if c != 'Total']
        row_max = max(row_vals) if row_vals else 0

        for col in cols:
            val = cross_df.loc[row_name].get(col, 0)
            is_total_cell = is_total or col == 'Total'
            is_diagonal = (row_name == col)
            is_max_migration = (val == row_max and val > 0 and not is_total_cell and not is_diagonal and row_name != 'Total')

            # Color logic
            if is_total_cell:
                bg_color = '#e8eaf6'
                font_weight = '700'
            elif is_diagonal:
                # Stayed in same segment — blue tint
                intensity = min(val / max_val, 1.0)
                r_c, g_c, b_c = 200, 220, 255
                bg_color = f'rgb({int(255-(255-r_c)*intensity*0.5)}, {int(255-(255-g_c)*intensity*0.5)}, {int(255-(255-b_c)*intensity*0.5)})'
                font_weight = '700'
            elif is_max_migration:
                # Largest migration — highlight pink/magenta
                bg_color = '#e1bee7'
                font_weight = '700'
            elif val > 0:
                intensity = min(val / max_val, 1.0)
                bg_color = f'rgba(233, 30, 99, {intensity * 0.15})'
                font_weight = '400'
            else:
                bg_color = '#fff'
                font_weight = '400'

            cell_style = f'padding:8px 6px; text-align:center; border:1px solid #ddd; background:{bg_color}; font-weight:{font_weight};'
            display_val = int(val) if val > 0 else ''
            html += f'<td style="{cell_style}">{display_val}</td>'
        html += '</tr>'

    html += '</table></div>'

    st.markdown(html, unsafe_allow_html=True)

    # Migration details expander
    if not merged_df.empty:
        with st.expander("📋 Detalhes de Migração (lista de contas)"):
            detail_cols = ['account_name', 'segmento_anterior', 'segmento_atual', 'valor_anterior', 'valor_atual']
            available = [c for c in detail_cols if c in merged_df.columns]
            changed = merged_df[merged_df['segmento_anterior'] != merged_df['segmento_atual']]
            if not changed.empty:
                st.dataframe(
                    changed[available].sort_values('valor_atual', ascending=False)
                    .style.format({'valor_anterior': 'R$ {:,.2f}', 'valor_atual': 'R$ {:,.2f}'}),
                    use_container_width=True
                )
            else:
                st.info("Nenhuma conta migrou de segmento entre os períodos.")


# ============================================================
# EXISTING CHARTS
# ============================================================

def plot_receita_mensal(df, date_col='data_pedido', val_col='valor_item'):
    if df.empty:
        return go.Figure()
    df_temp = df.copy()
    df_temp['Mes'] = df_temp[date_col].dt.to_period('M').astype(str)
    res = df_temp.groupby('Mes')[val_col].sum().reset_index()
    fig = px.bar(res, x='Mes', y=val_col,
                 title='Receita por Mês',
                 labels={val_col: 'Receita (R$)', 'Mes': 'Mês'},
                 color_discrete_sequence=['#4CAF50'])
    fig.update_yaxes(tickprefix="R$ ")
    return fig

def plot_segment_distribution(df_rfm):
    if df_rfm.empty:
         return go.Figure()
    res = df_rfm['segmento_rfm'].value_counts().reset_index()
    res.columns = ['Segmento', 'Quantidade']
    fig = px.pie(res, values='Quantidade', names='Segmento', hole=0.4, title='Distribuição de Contas por Segmento RFM')
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))
    return fig

def plot_rfm_scatter(df_rfm):
    if df_rfm.empty:
        return go.Figure()
    fig = px.scatter(df_rfm,
                     x='dias_desde_ultima_compra',
                     y='valor_total',
                     size='pedidos_unicos',
                     color='segmento_rfm',
                     hover_name='account_name',
                     hover_data=['R_score', 'F_score', 'M_score', 'vendedor_principal'],
                     title='Recência vs Valor (log, tamanho = Frequência)',
                     labels={'dias_desde_ultima_compra': 'Dias desde a última compra', 'valor_total': 'Valor Total (R$)'},
                     log_y=True, opacity=0.7, size_max=50)
    fig.update_yaxes(tickprefix="R$ ")
    return fig

def plot_rfm_heatmap(df_rfm):
    if df_rfm.empty:
        return go.Figure()
    heatmap_data = df_rfm.groupby(['R_score', 'M_score']).size().unstack(fill_value=0)
    fig = px.imshow(heatmap_data,
                    labels=dict(x="Score Monetário (M)", y="Score Recência (R)", color="Qtd Contas"),
                    x=[1, 2, 3, 4, 5], y=[1, 2, 3, 4, 5],
                    title="Heatmap: R Score vs M Score",
                    color_continuous_scale='RdYlGn', origin='lower')
    return fig

def plot_rfm_treemap(df_rfm):
    if df_rfm.empty:
        return go.Figure()
    res = df_rfm.groupby('segmento_rfm').agg(
        qtd_contas=('account_name', 'count'),
        valor_total=('valor_total', 'sum')
    ).reset_index()
    res['Carteira'] = 'Base de Clientes'
    fig = px.treemap(res, path=['Carteira', 'segmento_rfm'], values='qtd_contas',
                     color='valor_total', hover_data=['valor_total'],
                     color_continuous_scale='Blues',
                     title="Treemap: Contas por Segmento")
    fig.data[0].textinfo = 'label+value+percent parent'
    return fig

def plot_familia_produto(df, top_n=20):
    if df.empty:
        return go.Figure()
    fam_df = df.groupby('familia_produto')['valor_item'].sum().reset_index()
    fam_df = fam_df.sort_values('valor_item', ascending=False).head(top_n)
    fam_df = fam_df.sort_values('valor_item', ascending=True)
    fig = px.bar(fam_df, x='valor_item', y='familia_produto', orientation='h',
                 title=f'Top {top_n} Famílias de Produto por Receita',
                 labels={'valor_item': 'Receita (R$)', 'familia_produto': 'Família'},
                 color_discrete_sequence=['#1976D2'])
    fig.update_xaxes(tickprefix="R$ ")
    return fig

def plot_grupo_receita(df_rfm, top_n=15):
    if df_rfm.empty:
        return go.Figure()
    grp = df_rfm.groupby('grupo_economico').agg(
        valor_total=('valor_total', 'sum'),
        contas=('account_name', 'count')
    ).reset_index()
    grp = grp.sort_values('valor_total', ascending=False).head(top_n)
    grp = grp.sort_values('valor_total', ascending=True)
    fig = px.bar(grp, x='valor_total', y='grupo_economico', orientation='h',
                 title=f'Top {top_n} Grupos Econômicos por Receita',
                 labels={'valor_total': 'Receita (R$)', 'grupo_economico': 'Grupo'},
                 color_discrete_sequence=['#7B1FA2'])
    fig.update_xaxes(tickprefix="R$ ")
    return fig
