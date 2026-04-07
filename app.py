import streamlit as st
import pandas as pd
from utils import (
    load_data,
    apply_filters,
    calculate_kpis,
    top_risk_barchart,
    fraud_rate_by_transaction_type,
    fraud_rate_by_merchant_category,
    top_risk_transaction_count,
    transaction_fraud_trend,
    fraud_rate_trend,
    fraud_by_channel
)

st.set_page_config(layout="wide")

st.title("📊 Dashboard Antifraude")

# =========================
# 📦 CACHE
# =========================
@st.cache_data
def get_data():
    return load_data(
        "data/transactions.csv",
        "data/customers.csv"
    )

df = get_data()

# =========================
# 🔎 FILTROS
# =========================
st.subheader("🔎 Filtros")

col1, col2 = st.columns(2)

# Garantir tipo correto
df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

min_date = df['timestamp'].min().date()
max_date = df['timestamp'].max().date()

with col1:
    date_range = st.date_input(
        "Período",
        value=[min_date, max_date]
    )

with col2:
    if 'channel' in df.columns:
        channel = sorted(df['channel'].dropna().unique())
        selected_channels = st.multiselect(
            "Canal / Device",
            options=channel,
            default=channel
        )
    else:
        st.warning("Coluna 'channel' não encontrada")
        selected_channels = None

# PROCESSAMENTO

df_filtered = apply_filters(df, date_range, selected_channels)

total_volume, total_amount, fraud_rate = calculate_kpis(df_filtered)




# KPIs

col1, col2, col3 = st.columns(3)

col1.metric("🔢 Volume Total", f"{total_volume:,}")
col2.metric("💰 Valor Processado", f"${total_amount:,.2f}")
col3.metric("🚨 Taxa de Fraude", f"{fraud_rate:.2f}%")



st.divider()


# SÉRIE TEMPORAL

col_graph02, col_graph002 = st.columns(2) 

with col_graph02:
    st.subheader("📈 Tendência de Transações vs Fraudes")
    chart = transaction_fraud_trend(df_filtered)
    st.altair_chart(chart)    
with col_graph002:
    st.subheader("🚨 Taxa de Fraude (%) ao Longo do Tempo")
    chart = fraud_rate_trend(df_filtered)
    st.altair_chart(chart)


# RISCO

col_graph0, col_graph01 = st.columns(2)

with col_graph0:
    st.subheader("📊 Ranking de Clientes de Alto Risco")
    chart = top_risk_barchart(df_filtered)
    st.altair_chart(chart)
  
with col_graph01:
    st.subheader("🚨 Top Clientes: Risco vs Número de Transações")
    chart = top_risk_transaction_count(df)
    st.altair_chart(chart)    

col_graph02, col_graph002 = st.columns(2) 

with col_graph02:
    st.subheader("📈 Tendência de Transações vs Fraudes")
    chart = transaction_fraud_trend(df_filtered)
    st.altair_chart(chart)    
with col_graph002:
    st.subheader("🚨 Taxa de Fraude (%) ao Longo do Tempo")
    chart = fraud_rate_trend(df_filtered)
    st.altair_chart(chart)


# Divisão em abas para não poluir a tela
tab1, tab2 = st.tabs(["📊 Análise de Risco", "📋 Dados Transacionais"])

with tab1:
    col_graph1, col_graph2 = st.columns(2)
    with col_graph1:
        st.title("🚨 Taxa de Fraude por Tipo de Transação")
        chart = fraud_rate_by_transaction_type(df_filtered)
        st.altair_chart(chart)
    with col_graph2:
        st.title("🚨 Taxa de Fraude por Categoria de Merchant")
        chart = fraud_rate_by_merchant_category(df_filtered)
        st.altair_chart(chart) 


with tab2:
    st.subheader("📋 Dados")
    st.dataframe(df_filtered)





