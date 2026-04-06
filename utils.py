import pandas as pd

import altair as alt

def load_data(transactions_path, customers_path):
    df_transactions = pd.read_csv(transactions_path)
    df_customers = pd.read_csv(customers_path)

    # Tratamento
    df_transactions['timestamp'] = pd.to_datetime(df_transactions['timestamp'])
    df_transactions['data'] = df_transactions['timestamp'].dt.strftime('%d-%m-%Y')

    df_transactions['fraud_confirmed'] = df_transactions['fraud_confirmed'].fillna(2)

    # Merge
    df = df_transactions.merge(
        df_customers,
        on="customer_id",
        how="left"  
    )

    return df


def apply_filters(df, date_range, selected_channels=None):
    df_filtered = df[
        (df['timestamp'] >= pd.to_datetime(date_range[0])) &
        (df['timestamp'] <= pd.to_datetime(date_range[1]))
    ]

    if selected_channels is not None:
        df_filtered = df_filtered[df_filtered['channel'].isin(selected_channels)]

    return df_filtered


def calculate_kpis(df_filtered):
    total_volume = len(df_filtered)
    total_amount = df_filtered['amount'].sum()
   
    fraud_rate = ((df_filtered['fraud_confirmed'] == 1).sum() / total_volume)*100

    

    return total_volume, total_amount, fraud_rate

# Tendência (comparação com período anterior)
def calculate_trend(df, date_range, selected_channels=None):
    delta_days = (date_range[1] - date_range[0]).days

    prev_start = pd.to_datetime(date_range[0]) - pd.Timedelta(days=delta_days)
    prev_end = pd.to_datetime(date_range[0])

    df_prev = df[
        (df['timestamp'] >= prev_start) &
        (df['timestamp'] < prev_end)
    ]

    if selected_channels is not None:
        df_prev = df_prev[df_prev['channel'].isin(selected_channels)]

    prev_fraud_rate = df_prev['fraud_confirmed'].mean() * 100 if len(df_prev) > 0 else 0

    return prev_fraud_rate


def top_risk_barchart(df_filtered, top_n=10):
    # Garantir tipo string na coluna customer_id
    df_filtered['customer_id'] = df_filtered['customer_id'].astype(str)
    
    # Identificar clientes com fraude confirmada
    clientes_com_fraude = df_filtered[df_filtered['fraud_confirmed'] == 1]['customer_id'].unique()
    
    # Top clientes por risk_score
    top_risk = df_filtered[['customer_id', 'risk_score']].drop_duplicates().nlargest(top_n, 'risk_score').copy()
    
    # Cores: vermelho se já houve fraude, azul caso contrário
    top_risk['color'] = top_risk['customer_id'].apply(
        lambda x: 'orange' if x in clientes_com_fraude else 'skyblue'
    )
    # Média do risk_score
    media_risco = df_filtered['risk_score'].mean()
    
    # Gráfico de colunas
    bars = alt.Chart(top_risk).mark_bar().encode(
        x=alt.X('customer_id', sort='-y', title='Customer ID'),
        y=alt.Y('risk_score', title='Risk Score'),
        color=alt.Color('color', scale=None, legend=None)
    )
    
    # Linha da média com legenda
    linha_media = alt.Chart(top_risk).mark_rule(strokeDash=[4,4], size=2).encode(
        y='risk_score:Q',
        color=alt.value('green'),  # cor da linha
        tooltip=alt.Tooltip(value=f'Média: {media_risco:.2f}'),
    ).transform_calculate(
        risk_score=f"{media_risco}"
    ).properties(
        name='Média'
    )
    
    # Altair não cria legenda automática para mark_rule, então usamos layer + text
    # Criar um dataframe auxiliar para legenda
    media_df = top_risk[['customer_id']].copy()
    media_df['label'] = f"Média ({media_risco:.2f})"
    media_chart = alt.Chart(media_df).mark_rule(color='green', strokeWidth=2).encode(
        y=alt.datum(media_risco),
        size=alt.value(2),
        tooltip=alt.value(f"Média: {media_risco:.2f}")
    )
    # Combinar gráficos
    chart = bars + linha_media
    chart = chart.properties(width=400, height=450)
    
    return chart

def fraud_rate_by_transaction_type(df_filtered):
    """
    Cria um gráfico de colunas da taxa de fraude (%) por tipo de transação.
    
    df_filtered: dataframe mergeado (transactions + customers)
    """
    # Garantir colunas corretas
    df_filtered['transaction_type'] = df_filtered['transaction_type'].astype(str)
    df_filtered['fraud_confirmed'] = df_filtered['fraud_confirmed'].fillna(0)

    # Calcular total de transações e fraudes por tipo
    fraud_by_type = df_filtered.groupby('transaction_type').agg(
        total_transacoes=('transaction_id', 'count'),
        fraudes_confirmadas=('fraud_confirmed', 'sum')
    ).reset_index()

    # Calcular taxa de fraude %
    fraud_by_type['taxa_fraude_%'] = (fraud_by_type['fraudes_confirmadas'] / fraud_by_type['total_transacoes']) * 100

    # Ordenar do tipo com maior taxa
    fraud_by_type = fraud_by_type.sort_values(by='taxa_fraude_%', ascending=False)

    # Gráfico Altair
    chart = alt.Chart(fraud_by_type).mark_bar().encode(
        x=alt.X('transaction_type', sort='-y', title='Tipo de Transação'),
        y=alt.Y('taxa_fraude_%', title='Taxa de Fraude (%)'),
        color=alt.value('orange'),
        tooltip=[
            alt.Tooltip('transaction_type', title='Tipo de Transação'),
            alt.Tooltip('taxa_fraude_%', title='Taxa de Fraude (%)', format=".2f"),
            alt.Tooltip('total_transacoes', title='Total Transações'),
            alt.Tooltip('fraudes_confirmadas', title='Fraudes Confirmadas')
        ]
    ).properties(
        width=600,
        height=300,
        title='Taxa de Fraude (%) por Tipo de Transação'
    )

    return chart

def fraud_rate_by_merchant_category(df_filtered):
    """
    Cria um gráfico de colunas da taxa de fraude (%) por categoria de merchant.
    
    df: dataframe mergeado (transactions + customers)
    """
    # Garantir colunas corretas
    df_filtered['merchant_category'] = df_filtered['merchant_category'].astype(str)
    df_filtered['fraud_confirmed'] = df_filtered['fraud_confirmed'].fillna(0)

    # Calcular total de transações e fraudes por categoria
    fraud_by_category = df_filtered.groupby('merchant_category').agg(
        total_transacoes=('transaction_id', 'count'),
        fraudes_confirmadas=('fraud_confirmed', 'sum')
    ).reset_index()

    # Calcular taxa de fraude %
    fraud_by_category['taxa_fraude_%'] = (
        fraud_by_category['fraudes_confirmadas'] / fraud_by_category['total_transacoes']
    ) * 100

    # Ordenar do tipo com maior taxa
    fraud_by_category = fraud_by_category.sort_values(by='taxa_fraude_%', ascending=False)

    # Gráfico Altair
    chart = alt.Chart(fraud_by_category).mark_bar().encode(
        x=alt.X('merchant_category', sort='-y', title='Categoria de Merchant'),
        y=alt.Y('taxa_fraude_%', title='Taxa de Fraude (%)'),
        color=alt.value('darkorange'),
        tooltip=[
            alt.Tooltip('merchant_category', title='Categoria'),
            alt.Tooltip('taxa_fraude_%', title='Taxa de Fraude (%)', format=".2f"),
            alt.Tooltip('total_transacoes', title='Total Transações'),
            alt.Tooltip('fraudes_confirmadas', title='Fraudes Confirmadas')
        ]
    ).properties(
        width=600,
        height=300,
        title='Taxa de Fraude (%) por Categoria de Merchant'
    )

    return chart


def transaction_fraud_trend(df_filtered):
    """
    Gráfico de tendência: total de transações vs fraudes confirmadas por dia.
    Inclui linha de média de fraudes no período.
    
    df: dataframe mergeado (transactions + customers)
    """

    # =========================
    # 📅 Preparação de data
    # =========================
    df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'], errors='coerce')
    df_filtered = df_filtered.dropna(subset=['timestamp'])

    df_filtered['data_so'] = df_filtered['timestamp'].dt.date
    df_filtered['fraud_confirmed'] = df_filtered['fraud_confirmed'].fillna(0)

    # =========================
    # 📊 Agregação
    # =========================
    trend_data = df_filtered.groupby('data_so').agg(
        total_transacoes=('transaction_id', 'count'),
        fraudes_confirmadas=('fraud_confirmed', 'sum')
    ).reset_index()

    trend_data = trend_data.sort_values('data_so')

    # =========================
    # 📉 Média de fraude
    # =========================
    media_fraude = trend_data['fraudes_confirmadas'].mean()

    # =========================
    # 🔄 Transformar para formato longo (Altair)
    # =========================
    trend_long = trend_data.melt(
        id_vars='data_so',
        value_vars=['total_transacoes', 'fraudes_confirmadas'],
        var_name='tipo',
        value_name='quantidade'
    )

    # =========================
    # 📈 Linhas principais
    # =========================
    lines = alt.Chart(trend_long).mark_line(point=True).encode(
        x=alt.X('data_so:T', title='Data'),
        y=alt.Y('quantidade:Q', title='Quantidade'),
        color=alt.Color(
            'tipo:N',
            scale=alt.Scale(
                domain=['total_transacoes', 'fraudes_confirmadas'],
                range=['blue', 'red']
            ),
            legend=alt.Legend(title="Métricas")
        ),
        tooltip=[
            alt.Tooltip('data_so:T', title='Data'),
            alt.Tooltip('quantidade:Q', title='Quantidade'),
            alt.Tooltip('tipo:N', title='Tipo')
        ]
    )

    # =========================
    # 📏 Linha de média
    # =========================
    media_df = pd.DataFrame({
        'y': [media_fraude],
        'label': [f"Média Fraudes ({media_fraude:.2f})"]
    })

    mean_line = alt.Chart(media_df).mark_rule(
        color='gray',
        strokeDash=[4,4]
    ).encode(
        y='y:Q',
        tooltip=alt.Tooltip('y:Q', title='Média Fraudes', format=".2f")
    )

    # =========================
    # 📊 Combinar tudo
    # =========================
    chart = (lines + mean_line).properties(
        width=700,
        height=350,
        title='Tendência: Volume Total vs Fraudes Confirmadas por Dia'
    )

    return chart


def fraud_rate_trend(df_filtered):
    """
    Gráfico de tendência da taxa de fraude (%) por dia.
    Inclui linha de média do período.
    
    df: dataframe mergeado (transactions + customers)
    """

    # =========================
    # 📅 Preparação
    # =========================
    df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'], errors='coerce')
    df_filtered = df_filtered.dropna(subset=['timestamp'])

    df_filtered['data_so'] = df_filtered['timestamp'].dt.date
    df_filtered['fraud_confirmed'] = df_filtered['fraud_confirmed'].fillna(0)

    # =========================
    # 📊 Agregação
    # =========================
    trend_data = df_filtered.groupby('data_so').agg(
        total_transacoes=('transaction_id', 'count'),
        fraudes_confirmadas=('fraud_confirmed', 'sum')
    ).reset_index()

    # Calcular taxa de fraude (%)
    trend_data['taxa_fraude_%'] = (
        trend_data['fraudes_confirmadas'] / trend_data['total_transacoes']
    ) * 100

    trend_data = trend_data.sort_values('data_so')

    # =========================
    # 📉 Média
    # =========================
    media_taxa = trend_data['taxa_fraude_%'].mean()

    # =========================
    # 📈 Linha principal
    # =========================
    line = alt.Chart(trend_data).mark_line(point=True).encode(
        x=alt.X('data_so:T', title='Data'),
        y=alt.Y('taxa_fraude_%:Q', title='Taxa de Fraude (%)'),
        color=alt.value('red'),
        tooltip=[
            alt.Tooltip('data_so:T', title='Data'),
            alt.Tooltip('taxa_fraude_%:Q', title='Taxa de Fraude (%)', format=".2f"),
            alt.Tooltip('total_transacoes', title='Total Transações'),
            alt.Tooltip('fraudes_confirmadas', title='Fraudes Confirmadas')
        ]
    )

    # =========================
    # 📏 Linha da média
    # =========================
    media_df = pd.DataFrame({
        'y': [media_taxa]
    })

    mean_line = alt.Chart(media_df).mark_rule(
        color='gray',
        strokeDash=[4,4]
    ).encode(
        y='y:Q',
        tooltip=alt.Tooltip('y:Q', title='Média (%)', format=".2f")
    )

    # =========================
    # 📊 Combinar
    # =========================
    chart = (line + mean_line).properties(
        width=700,
        height=350,
        title='Tendência da Taxa de Fraude (%) por Dia'
    )

    return chart


def fraud_by_channel(df_filtered):
    if 'channel' in df_filtered.columns:
        return df_filtered.groupby('channel')['fraud_confirmed'].mean()
    return None
