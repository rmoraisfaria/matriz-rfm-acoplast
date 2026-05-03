import pandas as pd
import numpy as np
import re
import os
import unicodedata

# ============================================================
# LOADING & COLUMN NORMALIZATION
# ============================================================

def load_data(filepath):
    """Carrega o CSV tratando o separador, encoding e limpando nomes das colunas."""
    encodings = ['utf-8-sig', 'cp1252', 'latin-1', 'utf-8']
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(filepath, sep=';', encoding=enc, low_memory=False)
            break
        except Exception:
            continue

    if df is None:
        raise Exception("Erro ao carregar o arquivo CSV: nenhuma codificação funcionou.")

    df.columns = [col.strip() for col in df.columns]
    df = _normalize_column_names(df)
    return df


def _normalize_column_names(df):
    """Normaliza nomes de colunas para compatibilidade entre CSVs antigo e novo."""
    # Mapeamento: nome_canonico -> [variantes possíveis]
    aliases = {
        'Grupo':              ['Nome Empresa Grupo'],
        'Código Grupo':       ['Cód. Empresa Grupo'],
        'Código Prod/Serv':   ['Cód. Prod/Serv'],
    }

    for canonical, variants in aliases.items():
        if canonical not in df.columns:
            for variant in variants:
                if variant in df.columns:
                    df = df.rename(columns={variant: canonical})
                    break

    # Resolver colunas com encoding problemático via substring matching
    expected_patterns = {
        'Família do Produto': ['amil', 'roduto'],
        'Município':          ['unic', 'pio'],
        'Situação Pedido':    ['itua', 'edido'],
        'Situação Item':      ['itua', 'tem'],
    }
    resolved = {}
    for expected_col, patterns in expected_patterns.items():
        if expected_col not in df.columns:
            for col in df.columns:
                if col not in resolved and all(p.lower() in col.lower() for p in patterns):
                    resolved[col] = expected_col
                    break
    if resolved:
        df = df.rename(columns=resolved)
    return df


# ============================================================
# VALUE CONVERSION
# ============================================================

def convert_currency(val):
    """Converte valores no formato brasileiro (com ou sem prefixo R$) para float."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if val_str == '':
        return 0.0
    # Remove prefixo R$ e espaços
    val_str = val_str.replace('R$', '').strip()
    # Remove pontos de milhar e troca vírgula por ponto
    val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def convert_quantity(val):
    """Converte quantidade para float."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if val_str == '':
        return 0.0
    val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except ValueError:
        return 0.0


# ============================================================
# DATA CLEANING
# ============================================================

def clean_data(df):
    """Limpa e formata os dados base, compatível com ambos os formatos de CSV."""
    # 1. Remover linhas inválidas
    df = df[~df['N. Pedido'].astype(str).str.contains(r'\*\*\*', na=False)]
    df = df[~df['Cliente'].astype(str).str.contains(r'\*\*\*', na=False)]

    # 2. Valores monetários
    for col_name in ['Vlr Total Item', 'Vlr Unitário']:
        if col_name in df.columns:
            df[col_name] = df[col_name].apply(convert_currency)
    df['valor_item'] = df['Vlr Total Item'] if 'Vlr Total Item' in df.columns else 0.0
    df['valor_unitario'] = df['Vlr Unitário'] if 'Vlr Unitário' in df.columns else 0.0

    # 3. Quantidades
    df['qtde_solic'] = df['Qtde. Solic.'].apply(convert_quantity)
    df['quant_faturada'] = df['Quant. Faturada'].apply(convert_quantity) if 'Quant. Faturada' in df.columns else 0.0

    # 4. Pedido ID
    df['pedido_id'] = df['N. Pedido'].astype(str).str.strip()

    # 5. Converter Datas
    date_cols = ['Emissao', 'Data Entrega', 'Dt. Entrega Item', 'Data Faturamento', 'Info Plus  3', 'CFRT - Data Inclusão']
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].replace(['00/00/0000', '00/00/00', ''], pd.NaT)
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')

    df['data_pedido'] = df['Emissao']
    df['data_faturamento'] = df['Data Faturamento'] if 'Data Faturamento' in df.columns else pd.NaT

    # 6. Campos categóricos
    df['status_pedido'] = df['Situação Pedido'].fillna('Não informado') if 'Situação Pedido' in df.columns else 'Não informado'
    df['status_item'] = df['Situação Item'].fillna('Não informado') if 'Situação Item' in df.columns else 'Não informado'
    df['tipo_pedido'] = df['Tipo De Pedido'].fillna('Não informado') if 'Tipo De Pedido' in df.columns else 'Não informado'
    df['vendedor'] = df['Nome Vendedor'].fillna('Sem Vendedor') if 'Nome Vendedor' in df.columns else 'Sem Vendedor'
    df['uf'] = df['UF'].fillna('NI')
    df['municipio'] = df['Município'].fillna('Não informado') if 'Município' in df.columns else 'Não informado'
    df['produto'] = df['Nome Prod/Serv'].fillna('Produto não informado')
    df['codigo_produto'] = df['Código Prod/Serv'].fillna('') if 'Código Prod/Serv' in df.columns else ''
    df['codigo_cliente'] = df['Código Cliente'].fillna('') if 'Código Cliente' in df.columns else ''

    # 7. Novos campos (Grupo Econômico e Família de Produto)
    df['grupo_economico'] = df['Grupo'].fillna('Sem Grupo') if 'Grupo' in df.columns else 'Sem Grupo'
    df['codigo_grupo'] = df['Código Grupo'].fillna('') if 'Código Grupo' in df.columns else ''
    df['familia_produto'] = df['Família do Produto'].fillna('Sem Família') if 'Família do Produto' in df.columns else 'Sem Família'

    return df


# ============================================================
# NORMALIZATION & ACCOUNT KEYS
# ============================================================

def clean_cnpj(cnpj):
    if pd.isna(cnpj):
        return ""
    return re.sub(r'\D', '', str(cnpj))


def normalize_string(text):
    """Limpa e padroniza nomes de empresas."""
    if pd.isna(text):
        return ""
    text = str(text).upper().strip()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    terms_to_remove = [
        r'\bLTDA\b', r'\bS\.?A\.?\b', r'\bS/A\b', r'\bEIRELI\b', r'\bME\b', r'\bEPP\b',
        r'\bCOMERCIO\b', r'\bINDUSTRIA\b', r'\bSERVICOS\b', r'\bBRASIL\b', r'\bCIA\b',
        r'\bCOMPANHIA\b', r'\bCOM\b', r'\bIND\b'
    ]
    for term in terms_to_remove:
        text = re.sub(term, '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def create_normalization_columns(df):
    """Cria colunas úteis para unificação de contas."""
    df['cnpj_limpo'] = df['CNPJ'].apply(clean_cnpj) if 'CNPJ' in df.columns else ''
    df['raiz_cnpj'] = df['cnpj_limpo'].str[:8]
    df['cliente_normalizado'] = df['Cliente'].apply(normalize_string)
    df['grupo_economico_normalizado'] = df['grupo_economico'].apply(normalize_string)
    return df


def create_account_key(df, strategy, generic_groups=None):
    """
    Define a chave unificadora (account_key) e nome (account_name) da conta.
    Estratégias:
    - 'Sugerida': Grupo -> Raiz CNPJ -> Codigo Cliente -> Normalizado
    - 'Grupo Econômico': Une pelo Grupo
    - 'Raiz CNPJ': Une filiais pela raiz (8 dígitos)
    - 'CNPJ Individual': Cada CNPJ é uma conta separada
    - 'Unidade': Usa Código Cliente
    """
    if generic_groups is None:
        generic_groups = ["GRUPO REVENDAS", "CLIENTES NACIONAIS", "", "***", "SEM GRUPO"]
    generic_groups = [normalize_string(g) for g in generic_groups]

    def get_suggested_key(row):
        grupo = str(row['grupo_economico_normalizado']).strip()
        raiz = str(row['raiz_cnpj']).strip()
        cod = str(row['codigo_cliente']).strip()
        nome_norm = str(row['cliente_normalizado']).strip()
        if grupo and grupo not in generic_groups:
            return f"GRP_{grupo}", grupo, 'Grupo Econômico'
        if raiz:
            return f"RAIZ_{raiz}", nome_norm, 'Raiz CNPJ'
        if cod:
            return f"COD_{cod}", str(row['Cliente']), 'Código Cliente'
        return f"NOME_{nome_norm}", str(row['Cliente']), 'Nome Normalizado'

    def get_unit_key(row):
        cod = str(row['codigo_cliente']).strip()
        cnpj = str(row['cnpj_limpo']).strip()
        if cod:
            return f"COD_{cod}", str(row['Cliente']), 'Unidade (Código)'
        if cnpj:
            return f"CNPJ_{cnpj}", str(row['Cliente']), 'Unidade (CNPJ)'
        return f"NOME_{row['cliente_normalizado']}", str(row['Cliente']), 'Nome Normalizado'

    def get_cnpj_key(row):
        cnpj = str(row['cnpj_limpo']).strip()
        if cnpj:
            return f"CNPJ_{cnpj}", str(row['Cliente']), 'CNPJ Individual'
        return get_unit_key(row)

    def get_raiz_key(row):
        raiz = str(row['raiz_cnpj']).strip()
        if raiz:
            return f"RAIZ_{raiz}", row['cliente_normalizado'], 'Raiz CNPJ'
        return get_unit_key(row)

    def get_grupo_key(row):
        grupo = str(row['grupo_economico_normalizado']).strip()
        if grupo and grupo not in generic_groups:
            return f"GRP_{grupo}", grupo, 'Grupo Econômico'
        return get_raiz_key(row)

    strategy_map = {
        'Sugerida': get_suggested_key,
        'Unidade': get_unit_key,
        'CNPJ Individual': get_cnpj_key,
        'Raiz CNPJ': get_raiz_key,
        'Grupo Econômico': get_grupo_key,
    }
    key_func = strategy_map.get(strategy, get_suggested_key)

    keys, names, types = [], [], []
    for _, row in df.iterrows():
        k, n, t = key_func(row)
        keys.append(k)
        names.append(n)
        types.append(t)

    df['account_key'] = keys
    df['account_name'] = names
    df['account_type'] = types

    # Se existir account_mapping.csv, sobrepor
    mapping_path = 'data/account_mapping.csv' if os.path.exists('data/account_mapping.csv') else 'account_mapping.csv'
    if os.path.exists(mapping_path):
        try:
            mapping_df = pd.read_csv(mapping_path, sep=';', encoding='utf-8-sig')
            mapping_dict_key = dict(zip(mapping_df['source_value'], mapping_df['account_key_final']))
            mapping_dict_name = dict(zip(mapping_df['source_value'], mapping_df['account_name_final']))

            def apply_mapping(row):
                for val in [row['cnpj_limpo'], str(row['codigo_cliente']), row['grupo_economico']]:
                    if val in mapping_dict_key:
                        return mapping_dict_key[val], mapping_dict_name[val], 'Mapeamento Manual'
                return row['account_key'], row['account_name'], row['account_type']

            applied = df.apply(apply_mapping, axis=1)
            df['account_key'] = [x[0] for x in applied]
            df['account_name'] = [x[1] for x in applied]
            df['account_type'] = [x[2] for x in applied]
        except Exception as e:
            print(f"Aviso: Não foi possível aplicar o account_mapping.csv: {e}")

    return df


# ============================================================
# RFM CALCULATION
# ============================================================

def calculate_rfm(df, ref_date, date_col='Emissao', filter_statuses=None):
    """Calcula R, F, M por account_key."""
    if filter_statuses is None:
        filter_statuses = ['Faturado', 'Parcialmente faturado', 'Atendido']

    df_filtered = df[df['status_pedido'].isin(filter_statuses)].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    # Agrupamentos principais
    rfm = df_filtered.groupby('account_key').agg(
        data_ultima_compra=(date_col, 'max'),
        data_primeira_compra=(date_col, 'min'),
        pedidos_unicos=('pedido_id', 'nunique'),
        valor_total=('valor_item', 'sum'),
        itens_comprados=('valor_item', 'count'),
        produtos_distintos=('produto', 'nunique')
    ).reset_index()

    # Recency
    rfm['dias_desde_ultima_compra'] = (ref_date - rfm['data_ultima_compra']).dt.days
    rfm['dias_desde_ultima_compra'] = rfm['dias_desde_ultima_compra'].apply(lambda x: max(0, x))

    # Metadados da conta
    meta_aggs = {
        'account_name': ('account_name', 'first'),
        'account_type': ('account_type', 'first'),
        'qtde_unidades': ('codigo_cliente', 'nunique'),
        'qtde_cnpjs': ('cnpj_limpo', lambda x: x[x != ""].nunique()),
        'ufs_atuacao': ('uf', lambda x: ', '.join(sorted(x.dropna().unique()))),
        'municipios_atuacao': ('municipio', lambda x: ', '.join(sorted(x.dropna().unique()))),
        'grupo_economico': ('grupo_economico', 'first'),
    }
    meta = df.groupby('account_key').agg(**meta_aggs).reset_index()

    # Vendedor principal (por valor)
    vendedor_principal = df_filtered.groupby(['account_key', 'vendedor'])['valor_item'].sum().reset_index()
    vendedor_principal = vendedor_principal.sort_values(['account_key', 'valor_item'], ascending=[True, False])
    vend_prim = vendedor_principal.groupby('account_key').first().reset_index()[['account_key', 'vendedor']]
    vend_prim.rename(columns={'vendedor': 'vendedor_principal'}, inplace=True)

    # Vendedores relacionados
    vendedores_rel = df_filtered.groupby('account_key')['vendedor'].apply(lambda x: ', '.join(sorted(x.unique()))).reset_index()
    vendedores_rel.rename(columns={'vendedor': 'vendedores_relacionados'}, inplace=True)

    # Produto maior receita
    prod_principal = df_filtered.groupby(['account_key', 'produto'])['valor_item'].sum().reset_index()
    prod_principal = prod_principal.sort_values(['account_key', 'valor_item'], ascending=[True, False])
    prod_prim = prod_principal.groupby('account_key').first().reset_index()[['account_key', 'produto']]
    prod_prim.rename(columns={'produto': 'produto_maior_receita'}, inplace=True)

    # Família de produto principal
    fam_principal = df_filtered.groupby(['account_key', 'familia_produto'])['valor_item'].sum().reset_index()
    fam_principal = fam_principal.sort_values(['account_key', 'valor_item'], ascending=[True, False])
    fam_prim = fam_principal.groupby('account_key').first().reset_index()[['account_key', 'familia_produto']]
    fam_prim.rename(columns={'familia_produto': 'familia_principal'}, inplace=True)

    # Mesclar tudo
    rfm = pd.merge(rfm, meta, on='account_key', how='left')
    rfm = pd.merge(rfm, vend_prim, on='account_key', how='left')
    rfm = pd.merge(rfm, vendedores_rel, on='account_key', how='left')
    rfm = pd.merge(rfm, prod_prim, on='account_key', how='left')
    rfm = pd.merge(rfm, fam_prim, on='account_key', how='left')

    rfm['ticket_medio_pedido'] = rfm['valor_total'] / rfm['pedidos_unicos']

    # Meses com compra
    meses_compra = df_filtered.groupby('account_key')[date_col].apply(lambda x: x.dt.to_period('M').nunique()).reset_index()
    meses_compra.rename(columns={date_col: 'meses_com_compra'}, inplace=True)
    rfm = pd.merge(rfm, meses_compra, on='account_key', how='left')

    rfm.fillna(0, inplace=True)

    # Rankings
    total_receita = rfm['valor_total'].sum()
    rfm['participacao_receita'] = rfm['valor_total'] / total_receita if total_receita > 0 else 0
    rfm['ranking_receita'] = rfm['valor_total'].rank(ascending=False, method='min')
    rfm['ranking_frequencia'] = rfm['pedidos_unicos'].rank(ascending=False, method='min')
    rfm['ranking_recencia'] = rfm['dias_desde_ultima_compra'].rank(ascending=True, method='min')

    return rfm


# ============================================================
# RFM SEGMENTATION
# ============================================================

def classify_rfm_segment(df_rfm):
    """Gera scores de 1 a 5 e segmenta as contas."""
    if df_rfm.empty:
        return df_rfm
    df_rfm = df_rfm.copy()

    try:
        df_rfm['R_score'] = pd.qcut(df_rfm['dias_desde_ultima_compra'], 5, labels=[5, 4, 3, 2, 1], duplicates='drop')
    except ValueError:
        df_rfm['R_score'] = pd.qcut(df_rfm['dias_desde_ultima_compra'].rank(method='first'), 5, labels=[5, 4, 3, 2, 1])

    try:
        df_rfm['F_score'] = pd.qcut(df_rfm['pedidos_unicos'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    except (ValueError, Exception):
        df_rfm['F_score'] = 1

    try:
        df_rfm['M_score'] = pd.qcut(df_rfm['valor_total'], 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    except ValueError:
        df_rfm['M_score'] = pd.qcut(df_rfm['valor_total'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])

    df_rfm['R_score'] = df_rfm['R_score'].astype(int)
    df_rfm['F_score'] = df_rfm['F_score'].astype(int)
    df_rfm['M_score'] = df_rfm['M_score'].astype(int)

    df_rfm['RFM_score'] = df_rfm['R_score'].astype(str) + df_rfm['F_score'].astype(str) + df_rfm['M_score'].astype(str)
    df_rfm['RFM_total'] = df_rfm['R_score'] + df_rfm['F_score'] + df_rfm['M_score']

    def segment_account(r, f, m):
        if r >= 4 and f >= 4 and m >= 4:
            return 'Campeões'
        elif r >= 4 and m >= 4:
            return 'Grandes contas ativas'
        elif r <= 2 and m >= 4:
            return 'Contas estratégicas em risco'
        elif f >= 4 and m <= 2:
            return 'Contas frequentes de baixo valor'
        elif r >= 3 and f >= 3 and 2 <= m <= 3:
            return 'Oportunidade de expansão'
        elif r >= 4 and f <= 2:
            return 'Recém compradores'
        elif r <= 2 and f <= 2:
            return 'Hibernando'
        elif r == 1:
            return 'Inativos ou quase perdidos'
        else:
            return 'Manutenção'

    df_rfm['segmento_rfm'] = df_rfm.apply(lambda row: segment_account(row['R_score'], row['F_score'], row['M_score']), axis=1)
    return df_rfm


# ============================================================
# ACCOUNT ACTIONS
# ============================================================

def generate_account_actions(df_rfm):
    """Sugerir ações práticas baseadas na segmentação RFM."""
    if df_rfm.empty:
        return df_rfm
    df_rfm = df_rfm.copy()

    def get_action_rules(segment, m_score):
        if segment == 'Campeões':
            return ('Alta', 'Proteção e Cross-sell', 'Blindar relacionamento, mapear novas unidades, pedir indicação, negociar recorrência.', 7, 'Quinzenal')
        elif segment == 'Grandes contas ativas':
            return ('Alta', 'Expansão de Mix', 'Revisar histórico e buscar cross-sell em linhas não compradas.', 15, 'Mensal')
        elif segment == 'Contas estratégicas em risco':
            return ('Alta', 'Retenção Urgente', 'Contato consultivo imediato, entender queda de demanda, mapear novo comprador.', 7, 'Semanal até retomar')
        elif segment == 'Oportunidade de expansão':
            return ('Média', 'Crescimento de Ticket', 'Montar plano de crescimento, sugerir produtos complementares.', 15, 'Mensal')
        elif segment == 'Recém compradores':
            return ('Média', 'Onboarding', 'Pós-venda, entender aplicação e criar próxima oportunidade.', 15, 'Mensal')
        elif segment == 'Contas frequentes de baixo valor':
            return ('Média', 'Otimização de Margem', 'Aumentar ticket médio, sugerir pacote mínimo ou produtos de maior margem.', 30, 'Bimestral')
        elif segment == 'Hibernando':
            prio = 'Média' if m_score >= 3 else 'Baixa'
            return (prio, 'Reativação', 'Campanha de reativação ou abordagem de novidades.', 30, 'Trimestral')
        elif segment == 'Inativos ou quase perdidos':
            prio = 'Média' if m_score >= 4 else 'Baixa'
            return (prio, 'Limpeza/Resgate', 'Reativação estruturada via marketing ou repasse de carteira.', 30, 'Semestral')
        else:
            return ('Baixa', 'Acompanhamento', 'Manter no radar, contato sob demanda.', 30, 'Mensal')

    actions = df_rfm.apply(lambda row: get_action_rules(row['segmento_rfm'], row['M_score']), axis=1)
    df_rfm['prioridade_gestao'] = [x[0] for x in actions]
    df_rfm['motivo_prioridade'] = [x[1] for x in actions]
    df_rfm['proxima_acao_sugerida'] = [x[2] for x in actions]
    df_rfm['prazo_sugerido_contato'] = [x[3] for x in actions]
    df_rfm['cadencia_sugerida'] = [x[4] for x in actions]
    df_rfm['vendedor_responsavel'] = df_rfm['vendedor_principal']
    df_rfm['status_gestao'] = 'Pendente'
    df_rfm['observacoes_conta'] = ''
    return df_rfm


# ============================================================
# UTILITIES
# ============================================================

def format_currency(val):
    return f"R$ {val:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')


def generate_merge_suggestions(df):
    """Analisa a base e sugere contas que deveriam ser unificadas."""
    suggestions = []

    raiz_groups = df[df['raiz_cnpj'] != ""].groupby('raiz_cnpj')
    for raiz, group in raiz_groups:
        unidades = group['codigo_cliente'].nunique()
        cnpjs = group['cnpj_limpo'].nunique()
        if cnpjs > 1:
            clientes = group['cliente_normalizado'].unique()
            valor = group['valor_item'].sum()
            pedidos = group['pedido_id'].nunique()
            suggestions.append({
                'tipo_sugestao': 'Mesma Raiz CNPJ, múltiplos CNPJs',
                'chave_detectada': f"RAIZ_{raiz}",
                'clientes_envolvidos': ' | '.join(clientes),
                'cnpjs_envolvidos': cnpjs,
                'codigos_cliente_envolvidos': unidades,
                'valor_total': valor,
                'pedidos_unicos': pedidos,
                'recomendacao': 'Unir por raiz CNPJ',
                'justificativa': 'Várias filiais do mesmo grupo operando sob mesma raiz.'
            })

    nome_groups = df[df['cliente_normalizado'] != ""].groupby('cliente_normalizado')
    for nome, group in nome_groups:
        raizes = group['raiz_cnpj'].nunique()
        if raizes > 1:
            valor = group['valor_item'].sum()
            pedidos = group['pedido_id'].nunique()
            suggestions.append({
                'tipo_sugestao': 'Mesmo Nome, múltiplas raízes de CNPJ',
                'chave_detectada': f"NOME_{nome}",
                'clientes_envolvidos': nome,
                'cnpjs_envolvidos': group['cnpj_limpo'].nunique(),
                'codigos_cliente_envolvidos': group['codigo_cliente'].nunique(),
                'valor_total': valor,
                'pedidos_unicos': pedidos,
                'recomendacao': 'Revisar manualmente',
                'justificativa': 'Possível franqueado, nome genérico ou grupo econômico não mapeado.'
            })

    sug_df = pd.DataFrame(suggestions)
    if not sug_df.empty:
        sug_df = sug_df.sort_values('valor_total', ascending=False)
    return sug_df


def calculate_migration(df, date_col, statuses, pa_start, pa_end, pb_start, pb_end):
    """Calcula a migração de segmentos RFM entre dois períodos."""
    mask_a = (df[date_col].dt.date >= pa_start) & (df[date_col].dt.date <= pa_end)
    mask_b = (df[date_col].dt.date >= pb_start) & (df[date_col].dt.date <= pb_end)

    df_a = df[mask_a].copy()
    df_b = df[mask_b].copy()

    if df_a.empty or df_b.empty:
        return pd.DataFrame(), pd.DataFrame()

    ref_a = pd.to_datetime(pa_end) + pd.Timedelta(days=1)
    ref_b = pd.to_datetime(pb_end) + pd.Timedelta(days=1)

    rfm_a = calculate_rfm(df_a, ref_a, date_col, statuses)
    rfm_b = calculate_rfm(df_b, ref_b, date_col, statuses)

    if rfm_a.empty or rfm_b.empty:
        return pd.DataFrame(), pd.DataFrame()

    rfm_a = classify_rfm_segment(rfm_a)
    rfm_b = classify_rfm_segment(rfm_b)

    merged = pd.merge(
        rfm_a[['account_key', 'account_name', 'segmento_rfm', 'valor_total']],
        rfm_b[['account_key', 'account_name', 'segmento_rfm', 'valor_total']],
        on='account_key',
        how='outer',
        suffixes=('_anterior', '_atual')
    )

    merged['account_name'] = merged['account_name_atual'].fillna(merged['account_name_anterior'])
    merged['segmento_anterior'] = merged['segmento_rfm_anterior'].fillna('Novos Clientes')
    merged['segmento_atual'] = merged['segmento_rfm_atual'].fillna('Saíram / Inativos')
    merged['valor_anterior'] = merged['valor_total_anterior'].fillna(0)
    merged['valor_atual'] = merged['valor_total_atual'].fillna(0)

    cross = pd.crosstab(
        merged['segmento_anterior'],
        merged['segmento_atual'],
        margins=True,
        margins_name='Total'
    )

    return cross, merged
