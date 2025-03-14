import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Backtesting - Análise B3", layout="wide")

st.title("🔄 Backtesting de Estratégias")

# Sidebar para configurações
st.sidebar.header("Configurações do Backtesting")

# Seleção da ação
acoes_populares = {
    'PETR4.SA': 'Petrobras PN',
    'VALE3.SA': 'Vale ON',
    'ITUB4.SA': 'Itaú PN',
    'BBDC4.SA': 'Bradesco PN',
    'ABEV3.SA': 'Ambev ON',
    'MGLU3.SA': 'Magazine Luiza ON',
    'WEGE3.SA': 'WEG ON',
}

acao_selecionada = st.sidebar.selectbox(
    "Selecione uma ação:",
    options=list(acoes_populares.keys()),
    format_func=lambda x: f"{x} - {acoes_populares[x]}"
)

# Período de teste
periodo = st.sidebar.selectbox(
    "Período de teste:",
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

# Configurações da estratégia
st.sidebar.header("Parâmetros da Estratégia")

# RSI
rsi_period = st.sidebar.slider("Período RSI", min_value=2, max_value=30, value=14)
rsi_overbought = st.sidebar.slider("Sobrecompra", min_value=50, max_value=100, value=70)
rsi_oversold = st.sidebar.slider("Sobrevenda", min_value=0, max_value=50, value=30)

# MACD
macd_fast = st.sidebar.slider("MACD Rápido", min_value=5, max_value=20, value=12)
macd_slow = st.sidebar.slider("MACD Lento", min_value=20, max_value=40, value=26)
macd_signal = st.sidebar.slider("MACD Sinal", min_value=5, max_value=20, value=9)

# Stop Loss e Take Profit
stop_loss = st.sidebar.slider("Stop Loss (%)", min_value=1.0, max_value=10.0, value=2.0, step=0.5)
take_profit = st.sidebar.slider("Take Profit (%)", min_value=1.0, max_value=20.0, value=4.0, step=0.5)

# Capital inicial
capital_inicial = st.sidebar.number_input("Capital Inicial (R$)", min_value=1000.0, value=10000.0, step=1000.0)

@st.cache_data
def carregar_dados(ticker, periodo):
    """Carrega dados históricos da ação"""
    acao = yf.Ticker(ticker)
    hist = acao.history(period=periodo)
    
    # Remove registros sem dados (mercado fechado)
    hist = hist.dropna()
    
    # Verifica se há dados após a limpeza
    if len(hist) == 0:
        raise Exception("Não foi possível carregar dados para o período selecionado.")
    
    # Remove sábados e domingos
    hist = hist[hist.index.dayofweek < 5]
    
    # Verifica se ainda há dados após o processamento
    if len(hist) == 0:
        raise Exception("Não há dados disponíveis para o período selecionado.")
    
    return hist.dropna()

@st.cache_data
def calcular_indicadores(dados):
    """Calcula indicadores técnicos"""
    df = dados.copy()
    
    # RSI
    df['RSI'] = ta.momentum.rsi(df['Close'], window=rsi_period)
    
    # MACD
    df['MACD'] = ta.trend.macd_diff(df['Close'], 
                                   window_slow=macd_slow,
                                   window_fast=macd_fast,
                                   window_sign=macd_signal)
    df['MACD_Signal'] = ta.trend.macd_signal(df['Close'],
                                            window_slow=macd_slow,
                                            window_fast=macd_fast,
                                            window_sign=macd_signal)
    
    return df

def executar_backtest(dados, capital_inicial, stop_loss, take_profit):
    """Executa o backtesting da estratégia"""
    df = dados.copy()
    
    # Inicializar variáveis
    capital = capital_inicial
    posicao = 0  # 0: sem posição, 1: comprado, -1: vendido
    preco_entrada = 0
    operacoes = []
    
    for i in range(1, len(df)):
        preco_atual = df['Close'].iloc[i]
        
        # Sinais de entrada
        sinal_compra = (df['RSI'].iloc[i] < rsi_oversold and 
                       df['MACD'].iloc[i] > df['MACD_Signal'].iloc[i])
        
        sinal_venda = (df['RSI'].iloc[i] > rsi_overbought and 
                      df['MACD'].iloc[i] < df['MACD_Signal'].iloc[i])
        
        # Verificar stop loss e take profit
        if posicao != 0:
            variacao = ((preco_atual - preco_entrada) / preco_entrada) * 100
            
            if (posicao == 1 and variacao <= -stop_loss) or \
               (posicao == 1 and variacao >= take_profit) or \
               (posicao == -1 and variacao >= stop_loss) or \
               (posicao == -1 and variacao <= -take_profit):
                
                # Fechar posição
                resultado = capital * (variacao / 100)
                capital += resultado
                operacoes.append({
                    'data': df.index[i],
                    'tipo': 'Fechamento',
                    'preco': preco_atual,
                    'resultado': resultado,
                    'capital': capital
                })
                posicao = 0
                preco_entrada = 0
        
        # Executar operações
        if posicao == 0:  # Sem posição
            if sinal_compra:
                posicao = 1
                preco_entrada = preco_atual
                operacoes.append({
                    'data': df.index[i],
                    'tipo': 'Compra',
                    'preco': preco_atual,
                    'resultado': 0,
                    'capital': capital
                })
            elif sinal_venda:
                posicao = -1
                preco_entrada = preco_atual
                operacoes.append({
                    'data': df.index[i],
                    'tipo': 'Venda',
                    'preco': preco_atual,
                    'resultado': 0,
                    'capital': capital
                })
    
    return pd.DataFrame(operacoes)

def plotar_resultados(dados, operacoes):
    """Plota os resultados do backtesting"""
    fig = make_subplots(rows=2, cols=1, 
                        shared_xaxes=True,
                        vertical_spacing=0.05,
                        row_heights=[0.7, 0.3])
    
    # Gráfico de preços
    fig.add_trace(go.Candlestick(
        x=dados.index,
        open=dados['Open'],
        high=dados['High'],
        low=dados['Low'],
        close=dados['Close'],
        name='OHLC'
    ), row=1, col=1)
    
    # Adicionar pontos de entrada e saída
    for _, op in operacoes.iterrows():
        if op['tipo'] in ['Compra', 'Venda']:
            fig.add_trace(go.Scatter(
                x=[op['data']],
                y=[op['preco']],
                mode='markers',
                marker=dict(
                    symbol='triangle-up' if op['tipo'] == 'Compra' else 'triangle-down',
                    size=10,
                    color='green' if op['tipo'] == 'Compra' else 'red'
                ),
                name=op['tipo'],
                showlegend=False
            ))
    
    # Gráfico de capital
    fig.add_trace(go.Scatter(
        x=operacoes['data'],
        y=operacoes['capital'],
        name='Capital',
        line=dict(color='blue')
    ), row=2, col=1)
    
    fig.update_layout(
        template='plotly_dark',
        height=800,
        showlegend=True,
        title='Resultados do Backtesting'
    )
    
    return fig

try:
    # Carregar dados
    with st.spinner('Carregando dados...'):
        dados = carregar_dados(acao_selecionada, periodo)
        dados = calcular_indicadores(dados)
    
    # Executar backtesting
    operacoes = executar_backtest(dados, capital_inicial, stop_loss, take_profit)
    
    # Calcular métricas
    if len(operacoes) > 0:
        resultado_total = operacoes['resultado'].sum()
        retorno_total = (resultado_total / capital_inicial) * 100
        num_operacoes = len(operacoes[operacoes['tipo'].isin(['Compra', 'Venda'])])
        operacoes_lucrativas = len(operacoes[operacoes['resultado'] > 0])
        taxa_acerto = (operacoes_lucrativas / num_operacoes * 100) if num_operacoes > 0 else 0
        
        # Exibir métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Resultado Total",
                f"R$ {resultado_total:.2f}",
                f"{retorno_total:.2f}%"
            )
        
        with col2:
            st.metric(
                "Capital Final",
                f"R$ {operacoes['capital'].iloc[-1]:.2f}"
            )
        
        with col3:
            st.metric(
                "Número de Operações",
                f"{num_operacoes}"
            )
        
        with col4:
            st.metric(
                "Taxa de Acerto",
                f"{taxa_acerto:.1f}%"
            )
        
        # Plotar resultados
        fig = plotar_resultados(dados, operacoes)
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela de operações
        st.subheader("Histórico de Operações")
        st.dataframe(operacoes)
    else:
        st.warning("Nenhuma operação foi executada no período selecionado.")

except Exception as e:
    st.error(f"Erro ao executar backtesting: {str(e)}") 