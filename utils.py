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

    df = df.copy()

    # Garantir datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    # =========================
    # 📅 Ajuste correto de datas
    # =========================
    if len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)

        df_filtered = df[
            (df['timestamp'] >= start_date) &
            (df['timestamp'] < end_date)  # 👈 aqui está o fix
        ]
    else:
        df_filtered = df

    # =========================
    # 📡 Filtro de canal
    # =========================
    if selected_channels:
        df_filtered = df_filtered[df_filtered['channel'].isin(selected_channels)]

    return df_filtered

def calculate_kpis(df_filtered):
    total_volume = len(df_filtered)
    total_amount = df_filtered['amount'].sum()
   
    fraud_rate = ((df_filtered['fraud_confirmed'] == 1).sum() / total_volume)*100

    

    return total_volume, total_amount, fraud_rate



def top_risk_barchart(df_filtered, top_n=10):
    df_filtered = df_filtered.copy()

    # =========================
    # 🔧 Preparação
    # =========================
    df_filtered['customer_id'] = df_filtered['customer_id'].astype(str)

    clientes_com_fraude = df_filtered[df_filtered['fraud_confirmed'] == 1]['customer_id'].unique()

    top_risk = df_filtered[['customer_id', 'risk_score']].drop_duplicates().nlargest(top_n, 'risk_score').copy()

    # =========================
    # 🎯 Categoria (IMPORTANTE)
    # =========================
    top_risk['status'] = top_risk['customer_id'].apply(
        lambda x: 'Com Fraude' if x in clientes_com_fraude else 'Sem Fraude'
    )

    # Média
    media_risco = df_filtered['risk_score'].mean()

    # =========================
    # 📊 Barras
    # =========================
    bars = alt.Chart(top_risk).mark_bar().encode(
        x=alt.X('customer_id:N', sort='-y', title='Customer ID'),
        y=alt.Y('risk_score:Q', title='Risk Score'),
        color=alt.Color(
            'status:N',
            scale=alt.Scale(
                domain=['Com Fraude', 'Sem Fraude'],
                range=['lightcoral', 'skyblue']
            ),
            legend=alt.Legend(title="Status do Cliente")
        ),
        tooltip=['customer_id', 'risk_score', 'status']
    )

    # =========================
    # 📏 Linha de média (COM LEGENDA)
    # =========================
    media_df = pd.DataFrame({
        'y': [media_risco],
        'tipo': ['Média Risk Score']
    })

    mean_line = alt.Chart(media_df).mark_rule(
        strokeDash=[4,4],
        size=2
    ).encode(
        y='y:Q',
        color=alt.Color(
            'tipo:N',
            scale=alt.Scale(
                domain=['Média Risk Score'],
                range=['green']
            ),
            legend=alt.Legend(title=None)
        ),
        tooltip=alt.Tooltip('y:Q', title='Média', format=".2f")
    )

    # =========================
    # 📊 Combinar
    chart = (bars + mean_line).resolve_scale(
        color='independent'
    ).properties(
        width=400,
        height=450
)

    return chart

def top_risk_transaction_count(df_filtered, top_n=10):
    """
    Gráfico horizontal mostrando número de transações
    para os clientes com maior risk_score.
    
    Vermelho = possui fraude
    Azul = não possui fraude
    """

    df_filtered = df_filtered.copy()

    # =========================
    # 🔝 Top clientes por risco
    # =========================
    df_filtered['customer_id'] = df_filtered['customer_id'].astype(str)

    top_customers = (
        df_filtered[['customer_id', 'risk_score']]
        .drop_duplicates()
        .nlargest(top_n, 'risk_score')
    )

    top_ids = top_customers['customer_id'].tolist()

    # =========================
    # 🚨 Clientes com fraude
    # =========================
    clientes_com_fraude = set(
        df_filtered[df_filtered['fraud_confirmed'] == 1]['customer_id'].astype(str)
    )

    # =========================
    # 📊 Contagem de transações
    # =========================
    transaction_counts = (
        df_filtered[df_filtered['customer_id'].isin(top_ids)]
        .groupby('customer_id')
        .size()
        .reset_index(name='transaction_count')
    )

    # =========================
    # 🔗 Merge com risk_score
    # =========================
    final_df = transaction_counts.merge(
        top_customers,
        on='customer_id',
        how='left'
    )

    # =========================
    # 🎯 Categoria (para legenda)
    # =========================
    final_df['status'] = final_df['customer_id'].apply(
        lambda x: 'Com Fraude' if x in clientes_com_fraude else 'Sem Fraude'
    )

    # Ordenar por risk_score
    final_df = final_df.sort_values(by='risk_score', ascending=False)

    # =========================
    # 📊 Gráfico horizontal
    # =========================
    chart = alt.Chart(final_df).mark_bar().encode(
        y=alt.Y('customer_id:N', sort='-x', title='Customer ID'),
        x=alt.X('transaction_count:Q', title='Número de Transações'),
        color=alt.Color(
            'status:N',
            scale=alt.Scale(
                domain=['Com Fraude', 'Sem Fraude'],
                range=['lightcoral', 'skyblue']
            ),
            legend=alt.Legend(title="Status do Cliente")
        ),
        tooltip=[
            alt.Tooltip('customer_id', title='Customer ID'),
            alt.Tooltip('transaction_count', title='Transações'),
            alt.Tooltip('risk_score', title='Risk Score'),
            alt.Tooltip('status', title='Status')
        ]
    ).properties(
        width=600,
        height=400,
        title='Top Clientes por Risk Score vs Número de Transações'
    )

    return chart

def timechart_amount_by_fraud(df_filtered):
    """
    Série temporal do valor total (amount) por dia,
    segmentado por status de fraude.
    
    df: dataframe mergeado
    """

    df_filtered = df_filtered.copy()

    # =========================
    # 🧼 Preparação
    # =========================
    df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'], errors='coerce')
    df_filtered = df_filtered.dropna(subset=['timestamp'])

    df_filtered['fraud_confirmed'] = df_filtered['fraud_confirmed'].fillna(2)

    # =========================
    # 📊 Agregação diária
    # =========================
    df_daily = df_filtered.groupby(
        [pd.Grouper(key='timestamp', freq='D'), 'fraud_confirmed']
    )['amount'].sum().reset_index()

    # =========================
    # 🎯 Mapeamento de labels
    # =========================
    df_daily['status'] = df_daily['fraud_confirmed'].map({
        0: 'Não Fraude',
        1: 'Fraude',
        2: 'Desconhecido'
    })

    # =========================
    # 📈 Gráfico
    # =========================
    chart = alt.Chart(df_daily).mark_line(point=True).encode(
        x=alt.X('timestamp:T', title='Data'),
        y=alt.Y('amount:Q', title='Valor Total (Amount)'),
        color=alt.Color(
            'status:N',
            scale=alt.Scale(
                domain=['Não Fraude', 'Fraude', 'Desconhecido'],
                range=['skyblue', 'red', 'gray']
            ),
            legend=alt.Legend(title="Status de Fraude")
        ),
        tooltip=[
            alt.Tooltip('timestamp:T', title='Data'),
            alt.Tooltip('status:N', title='Status'),
            alt.Tooltip('amount:Q', title='Valor', format=",.2f")
        ]
    ).properties(
        width=700,
        height=350,
        title='Total Diário de Transações por Status de Fraude'
    )

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
    # =========================
    fraud_by_type = df_filtered.groupby('transaction_type').agg(
        total_transacoes=('transaction_id', 'count'),
        fraudes_confirmadas=('fraud_confirmed', 'sum')
    ).reset_index()

    # Calcular taxa de fraude (%)
    fraud_by_type['taxa_fraude_%'] = (
        fraud_by_type['fraudes_confirmadas'] / fraud_by_type['total_transacoes'] * 100
    )

    # =========================
    # 🔄 Transformar para barras lado a lado
    # =========================
    df_long = fraud_by_type.melt(
        id_vars='transaction_type',
        value_vars=['total_transacoes', 'fraudes_confirmadas'],
        var_name='tipo',
        value_name='valor'
    )

    df_long['tipo'] = df_long['tipo'].map({
        'total_transacoes': 'Total Transações',
        'fraudes_confirmadas': 'Fraudes Confirmadas'
    })

    # =========================
    # 📊 Barras agrupadas
    # =========================
    bars = alt.Chart(df_long).mark_bar().encode(
        x=alt.X('transaction_type:N', title='Tipo de Transação'),
        xOffset='tipo:N',  # lado a lado
        y=alt.Y('valor:Q', title='Quantidade'),
        color=alt.Color(
            'tipo:N',
            scale=alt.Scale(
                domain=['Total Transações', 'Fraudes Confirmadas'],
                range=['skyblue', 'red']
            ),
            legend=alt.Legend(title="Tipo")
        ),
        tooltip=[
            alt.Tooltip('transaction_type', title='Tipo de Transação'),
            alt.Tooltip('tipo', title='Tipo'),
            alt.Tooltip('valor', title='Quantidade')
        ]
    )

    # =========================
    # 📈 Linha de taxa de fraude
    # =========================
    line = alt.Chart(fraud_by_type).mark_line(point=True, size=2).encode(
        x=alt.X('transaction_type:N'),
        y=alt.Y('taxa_fraude_%:Q', title='Taxa de Fraude (%)'),
        color=alt.value('orange'),
        tooltip=[
            alt.Tooltip('transaction_type', title='Tipo de Transação'),
            alt.Tooltip('taxa_fraude_%:Q', title='Taxa de Fraude (%)', format=".2f")
        ]
    )

    # =========================
    # 📊 Combinar gráfico com eixo Y independente
    # =========================
    chart = alt.layer(
        bars, line
    ).resolve_scale(
        y='independent'
    ).properties(
        width=700,
        height=400,
        title='Transações e Fraudes por Tipo de Transação com Taxa (%)'
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

    fraud_by_category = df_filtered.groupby('merchant_category').agg(
        total_transacoes=('transaction_id', 'count'),
        fraudes_confirmadas=('fraud_confirmed', 'sum')
    ).reset_index()

    # Calcular taxa de fraude (%)
    fraud_by_category['taxa_fraude_%'] = (
        fraud_by_category['fraudes_confirmadas'] / fraud_by_category['total_transacoes'] * 100
    )

    # =========================
    # 🔄 Transformar para barras (lado a lado)
    # =========================
    df_long = fraud_by_category.melt(
        id_vars='merchant_category',
        value_vars=['total_transacoes', 'fraudes_confirmadas'],
        var_name='tipo',
        value_name='valor'
    )

    df_long['tipo'] = df_long['tipo'].map({
        'total_transacoes': 'Total Transações',
        'fraudes_confirmadas': 'Fraudes Confirmadas'
    })

    # =========================
    # 📊 Barras lado a lado
    # =========================
    bars = alt.Chart(df_long).mark_bar().encode(
        x=alt.X('merchant_category:N', title='Categoria de Merchant'),
        xOffset='tipo:N',  # faz agrupamento lado a lado
        y=alt.Y('valor:Q', title='Quantidade'),
        color=alt.Color(
            'tipo:N',
            scale=alt.Scale(
                domain=['Total Transações', 'Fraudes Confirmadas'],
                range=['skyblue', 'red']
            ),
            legend=alt.Legend(title="Tipo")
        ),
        tooltip=[
            alt.Tooltip('merchant_category', title='Categoria'),
            alt.Tooltip('tipo', title='Tipo'),
            alt.Tooltip('valor', title='Quantidade')
        ]
    )

    # =========================
    # 📈 Linha de taxa de fraude
    # =========================
    line = alt.Chart(fraud_by_category).mark_line(point=True, size=2).encode(
        x=alt.X('merchant_category:N'),
        y=alt.Y('taxa_fraude_%:Q', title='Taxa de Fraude (%)'),
        color=alt.value('orange'),
        tooltip=[
            alt.Tooltip('merchant_category', title='Categoria'),
            alt.Tooltip('taxa_fraude_%:Q', title='Taxa de Fraude (%)', format=".2f")
        ]
    )

    # =========================
    # 📊 Combinar com dual-axis
    # =========================
    chart = alt.layer(
        bars, line
    ).resolve_scale(
        y='independent'  # eixo Y separado para taxa
    ).properties(
        width=700,
        height=400,
        title='Transações e Fraudes por Categoria com Taxa (%)'
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
        fraudes_confirmadas=('fraud_confirmed', lambda x: (x == 1).sum())
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
