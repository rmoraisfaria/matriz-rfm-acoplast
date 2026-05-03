import sys
from data_processing import load_data, clean_data, convert_currency

filepath = 'data/Relatório Vendas 2025.csv'
df_raw = load_data(filepath)
print(f"Raw rows: {len(df_raw)}")

df_clean = clean_data(df_raw)
print(f"Valid rows: {len(df_clean)}")

total_geral = df_clean['valor_item'].sum()
print(f"Total geral válido: R$ {total_geral:,.2f}")

faturado = df_clean[df_clean['status_pedido'] == 'Faturado']['valor_item'].sum()
print(f"Total Faturado: R$ {faturado:,.2f}")

fat_parc_aten = df_clean[df_clean['status_pedido'].isin(['Faturado', 'Parcialmente faturado', 'Atendido'])]['valor_item'].sum()
print(f"Total Faturado+Parc+Aten: R$ {fat_parc_aten:,.2f}")

pedidos_unicos = df_clean['pedido_id'].nunique()
print(f"Pedidos unicos: {pedidos_unicos}")
