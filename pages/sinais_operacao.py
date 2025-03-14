import streamlit as st
import pandas as pd
import numpy as np
import ta
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="Sinais de Operação", layout="wide")

st.title("🎯 Sinais de Operação")

# Sidebar para seleção de ações
st.sidebar.header("Configurações")

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
    "Período de análise:",
    options=['1mo', '3mo', '6mo', '1y'],
    format_func=lambda x: {
        '1mo': '1 Mês',
        '3mo': '3 Meses',
        '6mo': '6 Meses',
        '1y': '1 Ano'
    }[x]
)

# Adicionar configurações de alertas na sidebar
st.sidebar.header("Configurações de Alertas")
alertas_config = carregar_alertas()

# Configurações de alertas
st.sidebar.subheader("🔔 Alertas")
ativar_alertas = st.sidebar.checkbox("Ativar Sistema de Alertas", value=alertas_config.get('ativado', False))

if ativar_alertas:
    score_minimo = st.sidebar.slider(
        "Score Mínimo para Alerta de Compra",
        min_value=-5,
        max_value=5,
        value=alertas_config.get('score_minimo', 3)
    )
    
    score_maximo = st.sidebar.slider(
        "Score Máximo para Alerta de Venda",
        min_value=-5,
        max_value=5,
        value=alertas_config.get('score_maximo', -3)
    )
    
    # Salvar configurações
    alertas_config = {
        'ativado': ativar_alertas,
        'score_minimo': score_minimo,
        'score_maximo': score_maximo
    }
    salvar_alertas(alertas_config)

# Abas principais
tab1, tab2, tab3 = st.tabs([
    "🔄 Momentum Trading",
    "📊 Price Action",
    "📈 Tendências"
])

# Função para carregar dados
@st.cache_data
def carregar_dados(ticker, periodo):
    acao = yf.Ticker(ticker)
    hist = acao.history(period=periodo)
    return hist

# Função para análise de momentum
def analisar_momentum(dados, rsi_compra=30, rsi_venda=70, macd_fast=12, macd_slow=26):
    df = dados.copy()
    
    # Calcular indicadores
    df['RSI'] = ta.momentum.rsi(df['Close'])
    df['MACD'] = ta.trend.macd_diff(df['Close'], 
                                   window_slow=macd_slow,
                                   window_fast=macd_fast)
    
    # Gerar sinais
    df['sinal_rsi'] = np.where(df['RSI'] < rsi_compra, 1,
                              np.where(df['RSI'] > rsi_venda, -1, 0))
    
    df['sinal_macd'] = np.where(df['MACD'] > 0, 1,
                               np.where(df['MACD'] < 0, -1, 0))
    
    return df

# Função para análise de price action
def analisar_price_action(dados):
    df = dados.copy()
    
    # Cálculos básicos
    df['body'] = abs(df['Close'] - df['Open'])
    df['upper_wick'] = df.apply(lambda x: x['High'] - max(x['Open'], x['Close']), axis=1)
    df['lower_wick'] = df.apply(lambda x: min(x['Open'], x['Close']) - x['Low'], axis=1)
    df['range_total'] = df['High'] - df['Low']
    
    # Detectar padrões
    df['doji'] = (df['body'] <= 0.1 * df['range_total'])
    df['pin_bar'] = (df['range_total'] > 3 * df['body'])
    
    return df

# Função para análise de tendências
def analisar_tendencias(dados, mm_curta=20, mm_longa=50):
    df = dados.copy()
    
    # Médias móveis
    df[f'MM{mm_curta}'] = ta.trend.sma_indicator(df['Close'], window=mm_curta)
    df[f'MM{mm_longa}'] = ta.trend.sma_indicator(df['Close'], window=mm_longa)
    
    # ATR para volatilidade
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'])
    
    return df

# Função para carregar configurações de alertas
def carregar_alertas():
    if os.path.exists('alertas_config.json'):
        with open('alertas_config.json', 'r') as f:
            return json.load(f)
    return {}

# Função para salvar configurações de alertas
def salvar_alertas(alertas):
    with open('alertas_config.json', 'w') as f:
        json.dump(alertas, f)

# Função para calcular score geral
def calcular_score_geral(dados_momentum, dados_pa, dados_tend):
    score = 0
    
    # Score do RSI
    if dados_momentum['sinal_rsi'].iloc[-1] == 1:
        score += 2
    elif dados_momentum['sinal_rsi'].iloc[-1] == -1:
        score -= 2
    
    # Score do MACD
    if dados_momentum['sinal_macd'].iloc[-1] == 1:
        score += 2
    elif dados_momentum['sinal_macd'].iloc[-1] == -1:
        score -= 2
    
    # Score de Price Action
    if dados_pa['doji'].iloc[-1]:
        score += 1 if dados_pa['Close'].iloc[-1] > dados_pa['Open'].iloc[-1] else -1
    
    # Score de Tendência
    if dados_tend[f'MM20'].iloc[-1] > dados_tend[f'MM50'].iloc[-1]:
        score += 1
    else:
        score -= 1
    
    return score

try:
    # Carregar dados
    dados = carregar_dados(acao_selecionada, periodo)
    
    with tab1:
        st.subheader("Análise de Momentum")
        
        col1, col2 = st.columns(2)
        with col1:
            rsi_compra = st.slider("RSI - Nível de Sobrevenda", 20, 40, 30)
            rsi_venda = st.slider("RSI - Nível de Sobrecompra", 60, 80, 70)
        
        with col2:
            macd_fast = st.slider("MACD - Média Rápida", 5, 15, 12)
            macd_slow = st.slider("MACD - Média Lenta", 20, 30, 26)
        
        # Análise de Momentum
        dados_momentum = analisar_momentum(dados, rsi_compra, rsi_venda, macd_fast, macd_slow)
        
        # Plotar gráficos
        fig = make_subplots(rows=3, cols=1, 
                           shared_xaxes=True,
                           vertical_spacing=0.05,
                           row_heights=[0.5, 0.25, 0.25])
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=dados.index,
            open=dados['Open'],
            high=dados['High'],
            low=dados['Low'],
            close=dados['Close'],
            name='Preço'
        ), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(
            x=dados.index,
            y=dados_momentum['RSI'],
            name='RSI'
        ), row=2, col=1)
        
        # MACD
        fig.add_trace(go.Scatter(
            x=dados.index,
            y=dados_momentum['MACD'],
            name='MACD'
        ), row=3, col=1)
        
        fig.update_layout(height=800, template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar sinais atuais
        st.subheader("Sinais Atuais")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Sinal RSI", 
                     "Compra" if dados_momentum['sinal_rsi'].iloc[-1] == 1 else
                     "Venda" if dados_momentum['sinal_rsi'].iloc[-1] == -1 else
                     "Neutro")
        with col2:
            st.metric("Sinal MACD",
                     "Compra" if dados_momentum['sinal_macd'].iloc[-1] == 1 else
                     "Venda" if dados_momentum['sinal_macd'].iloc[-1] == -1 else
                     "Neutro")
        
        # Adicionar seção de score e alertas
        st.subheader("Score e Alertas")
        
        # Calcular scores
        dados_pa = analisar_price_action(dados)
        dados_tend = analisar_tendencias(dados)
        
        score_geral = calcular_score_geral(dados_momentum, dados_pa, dados_tend)
        
        # Mostrar score atual
        st.metric("Score Geral", score_geral)
        
        # Mostrar alertas se ativados
        if ativar_alertas:
            if score_geral >= score_minimo:
                st.success(f"🚨 ALERTA DE COMPRA! Score: {score_geral}")
            elif score_geral <= score_maximo:
                st.error(f"🚨 ALERTA DE VENDA! Score: {score_geral}")
        
        # Mostrar breakdown do score
        st.subheader("Breakdown do Score")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("RSI", 
                     "Compra" if dados_momentum['sinal_rsi'].iloc[-1] == 1 else
                     "Venda" if dados_momentum['sinal_rsi'].iloc[-1] == -1 else
                     "Neutro")
        
        with col2:
            st.metric("MACD",
                     "Compra" if dados_momentum['sinal_macd'].iloc[-1] == 1 else
                     "Venda" if dados_momentum['sinal_macd'].iloc[-1] == -1 else
                     "Neutro")
        
        with col3:
            st.metric("Price Action",
                     "Compra" if dados_pa['doji'].iloc[-1] and dados_pa['Close'].iloc[-1] > dados_pa['Open'].iloc[-1] else
                     "Venda" if dados_pa['doji'].iloc[-1] and dados_pa['Close'].iloc[-1] < dados_pa['Open'].iloc[-1] else
                     "Neutro")
        
        with col4:
            st.metric("Tendência",
                     "Alta" if dados_tend[f'MM20'].iloc[-1] > dados_tend[f'MM50'].iloc[-1] else
                     "Baixa")
    
    with tab2:
        st.subheader("Análise Price Action")
        dados_pa = analisar_price_action(dados)
        # Implementar visualização de Price Action
        
    with tab3:
        st.subheader("Análise de Tendências")
        dados_tend = analisar_tendencias(dados)
        # Implementar visualização de Tendências

except Exception as e:
    st.error(f"Erro ao processar dados: {str(e)}") 