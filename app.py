import streamlit as st
from utils import (
    load_data,
    apply_filters,
    calculate_kpis,
    calculate_trend,
    top_risk_barchart,
    fraud_rate_by_transaction_type,
    fraud_rate_by_merchant_category,
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

min_date = df['timestamp'].min()
max_date = df['timestamp'].max()

with col1:
    date_range = st.date_input("Período", [min_date, max_date])

with col2:
    if 'channel' in df.columns:
        channel = df['channel'].dropna().unique()
        selected_devices = st.multiselect(
            "Canal / Device",
            options=channel,
            default=channel
        )
    else:
        st.warning("Coluna 'device' não encontrada")
        selected_devices = None

# =========================
# 📊 PROCESSAMENTO
# =========================
df_filtered = apply_filters(df, date_range, selected_devices)

total_volume, total_amount, fraud_rate = calculate_kpis(df_filtered)

prev_fraud_rate = calculate_trend(df, date_range, selected_devices)


# =========================
# 📊 KPIs
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("🔢 Volume Total", f"{total_volume:,}")
col2.metric("💰 Valor Processado", f"${total_amount:,.2f}")
col3.metric("🚨 Taxa de Fraude", f"{fraud_rate:.2f}%")



st.divider()

# =========================
# 📈 SÉRIE TEMPORAL
# =========================
st.subheader("📊 Ranking de Clientes de Alto Risco")

if total_volume > 0:
    chart = top_risk_barchart(df)
    st.altair_chart(chart)
else:
    st.warning("Sem dados para os filtros selecionados.")


st.subheader("📈 Tendência de Transações vs Fraudes")
chart = transaction_fraud_trend(df)
st.altair_chart(chart)    

st.subheader("🚨 Taxa de Fraude (%) ao Longo do Tempo")
chart = fraud_rate_trend(df)
st.altair_chart(chart)


# Divisão em abas para não poluir a tela
tab1, tab2 = st.tabs(["📊 Análise de Risco", "📋 Dados Transacionais"])

with tab1:
    col_graph1, col_graph2 = st.columns(2)
    with col_graph1:
        st.title("🚨 Taxa de Fraude por Tipo de Transação")
        chart = fraud_rate_by_transaction_type(df)
        st.altair_chart(chart)
    with col_graph2:
        st.title("🚨 Taxa de Fraude por Categoria de Merchant")
        chart = fraud_rate_by_merchant_category(df)
        st.altair_chart(chart) 


with tab2:
    st.subheader("📋 Dados")
    st.dataframe(df_filtered)





