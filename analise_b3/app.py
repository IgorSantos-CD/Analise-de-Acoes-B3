import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="Análise B3", layout="wide")

st.title("📈 Análise de Ações B3")

# Sidebar para seleção de ações
st.sidebar.header("Filtros")

# Lista de algumas ações populares da B3
acoes_populares = {
    'PETR4.SA': 'Petrobras PN',
    'VALE3.SA': 'Vale ON',
    'ITUB4.SA': 'Itaú PN',
    'BBDC4.SA': 'Bradesco PN',
    'ABEV3.SA': 'Ambev ON',
    'MGLU3.SA': 'Magazine Luiza ON',
    'WEGE3.SA': 'WEG ON',
}

# Seleção da ação
acao_selecionada = st.sidebar.selectbox(
    "Selecione uma ação:",
    options=list(acoes_populares.keys()),
    format_func=lambda x: f"{x} - {acoes_populares[x]}"
)

# Período de análise
periodo = st.sidebar.selectbox(
    "Selecione o período de análise:",
    options=['1mo', '3mo', '6mo', '1y', '2y', '5y'],
    format_func=lambda x: {
        '1mo': '1 Mês',
        '3mo': '3 Meses',
        '6mo': '6 Meses',
        '1y': '1 Ano',
        '2y': '2 Anos',
        '5y': '5 Anos'
    }[x]
)

# Intervalo das velas
intervalo_velas = st.sidebar.selectbox(
    "Intervalo das velas:",
    options=['1d', '1h', '5d', '1wk', '1mo'],
    format_func=lambda x: {
        '1d': 'Diário',
        '1h': '1 Hora',
        '5d': '5 Dias',
        '1wk': 'Semanal',
        '1mo': 'Mensal'
    }[x]
)

@st.cache_data
# Função para carregar dados das ações  
def carregar_dados(ticker, periodo, intervalo):
    acao = yf.Ticker(ticker)
    hist = acao.history(period=periodo, interval=intervalo)
    return hist, acao.info


try:
    # Carregando dados
    with st.spinner('Carregando dados...'):
        dados, info = carregar_dados(acao_selecionada, periodo, intervalo_velas)
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Preço Atual",
            f"R$ {dados['Close'].iloc[-1]:.2f}",
            f"{((dados['Close'].iloc[-1] - dados['Close'].iloc[-2]) / dados['Close'].iloc[-2] * 100):.2f}%"
        )
    
    with col2:
        st.metric(
            "Volume Médio (30d)",
            f"{dados['Volume'].mean():,.0f}"
        )
    
    with col3:
        st.metric(
            "Máxima do Período",
            f"R$ {dados['High'].max():.2f}"
        )
    
    with col4:
        st.metric(
            "Mínima do Período",
            f"R$ {dados['Low'].min():.2f}"
        )

    # Gráfico de candlestick
    intervalo_nome = {
        '1d': 'Diário',
        '1h': 'Uma Hora',
        '5d': '5 Dias',
        '1wk': 'Semanal',
        '1mo': 'Mensal'
    }
    st.subheader(f"Gráfico de Candlestick ({intervalo_nome[intervalo_velas]})")
    fig = go.Figure(data=[go.Candlestick(x=dados.index,
                open=dados['Open'],
                high=dados['High'],
                low=dados['Low'],
                close=dados['Close'])])
    
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Análise de retornos
    st.subheader("Análise de Retornos")
    retornos = dados['Close'].pct_change()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Retorno Total do Período",
            f"{((dados['Close'].iloc[-1] / dados['Close'].iloc[0] - 1) * 100):.2f}%"
        )
    
    with col2:
        st.metric(
            "Volatilidade (Desvio Padrão)",
            f"{(retornos.std() * 100):.2f}%"
        )

    # Volume
    st.subheader("Volume de Negociação")
    fig_volume = go.Figure(data=[go.Bar(x=dados.index, y=dados['Volume'])])
    fig_volume.update_layout(
        template='plotly_dark',
        height=400
    )
    st.plotly_chart(fig_volume, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {str(e)}")

# Adiciona footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Desenvolvido para análise de ações da B3 🚀</p>
    <p>Os dados são fornecidos pelo Yahoo Finance e podem ter atraso em relação ao mercado.</p>
</div>
""", unsafe_allow_html=True)