import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from itertools import product

st.set_page_config(page_title="Otimização - Análise B3", layout="wide")

st.title("⚙️ Otimização de Estratégias")

# Função para carregar configurações salvas
def carregar_configuracoes():
    if os.path.exists('configuracoes.json'):
        with open('configuracoes.json', 'r') as f:
            return json.load(f)
    return {}

# Função para salvar configurações
def salvar_configuracoes(config):
    with open('configuracoes.json', 'w') as f:
        json.dump(config, f, indent=4)

# Sidebar para configurações
st.sidebar.header("Configurações da Otimização")

# Seleção da ação
acoes_populares = {
    'IBOV.SA': 'Índice Bovespa',
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

# Configurações de otimização
st.sidebar.header("Parâmetros para Otimização")

# RSI
rsi_period_range = st.sidebar.slider(
    "Período RSI (min-max)",
    min_value=2,
    max_value=30,
    value=(10, 20)
)
rsi_overbought_range = st.sidebar.slider(
    "Sobrecompra (min-max)",
    min_value=50,
    max_value=100,
    value=(60, 80)
)
rsi_oversold_range = st.sidebar.slider(
    "Sobrevenda (min-max)",
    min_value=0,
    max_value=50,
    value=(20, 40)
)

# MACD
macd_fast_range = st.sidebar.slider(
    "MACD Rápido (min-max)",
    min_value=5,
    max_value=20,
    value=(8, 16)
)
macd_slow_range = st.sidebar.slider(
    "MACD Lento (min-max)",
    min_value=20,
    max_value=40,
    value=(20, 30)
)
macd_signal_range = st.sidebar.slider(
    "MACD Sinal (min-max)",
    min_value=5,
    max_value=20,
    value=(7, 12)
)

# Stop Loss e Take Profit
stop_loss_range = st.sidebar.slider(
    "Stop Loss (min-max %)",
    min_value=1.0,
    max_value=10.0,
    value=(1.5, 3.0),
    step=0.5
)
take_profit_range = st.sidebar.slider(
    "Take Profit (min-max %)",
    min_value=1.0,
    max_value=20.0,
    value=(3.0, 6.0),
    step=0.5
)

# Capital inicial
capital_inicial = st.sidebar.number_input(
    "Capital Inicial (R$)",
    min_value=1000.0,
    value=10000.0,
    step=1000.0
)

# Número de combinações para testar
num_combinacoes = st.sidebar.number_input(
    "Número de combinações para testar",
    min_value=10,
    max_value=1000,
    value=100,
    step=10
)

@st.cache_data
def carregar_dados(ticker, periodo):
    """Carrega dados históricos da ação"""
    acao = yf.Ticker(ticker)
    hist = acao.history(period=periodo)
    return hist.dropna()

@st.cache_data
def calcular_indicadores(dados, params):
    """Calcula indicadores técnicos com parâmetros específicos"""
    df = dados.copy()
    
    # RSI
    df['RSI'] = ta.momentum.rsi(df['Close'], window=params['rsi_period'])
    
    # MACD
    df['MACD'] = ta.trend.macd_diff(df['Close'], 
                                   window_slow=params['macd_slow'],
                                   window_fast=params['macd_fast'],
                                   window_sign=params['macd_signal'])
    df['MACD_Signal'] = ta.trend.macd_signal(df['Close'],
                                            window_slow=params['macd_slow'],
                                            window_fast=params['macd_fast'],
                                            window_sign=params['macd_signal'])
    
    return df

def detectar_suportes_resistencias(dados, sensitivity=0.5):
    """Detecta níveis de suporte e resistência"""
    df = dados.copy()
    
    # Identificar pivots
    df['pivot'] = False
    for i in range(2, len(df)-2):
        # Pivot de alta (resistência)
        if (df['High'].iloc[i] > df['High'].iloc[i-1] and 
            df['High'].iloc[i] > df['High'].iloc[i-2] and
            df['High'].iloc[i] > df['High'].iloc[i+1] and 
            df['High'].iloc[i] > df['High'].iloc[i+2]):
            df.loc[df.index[i], 'pivot'] = True
            df.loc[df.index[i], 'pivot_type'] = 'resistance'
        
        # Pivot de baixa (suporte)
        if (df['Low'].iloc[i] < df['Low'].iloc[i-1] and 
            df['Low'].iloc[i] < df['Low'].iloc[i-2] and
            df['Low'].iloc[i] < df['Low'].iloc[i+1] and 
            df['Low'].iloc[i] < df['Low'].iloc[i+2]):
            df.loc[df.index[i], 'pivot'] = True
            df.loc[df.index[i], 'pivot_type'] = 'support'
    
    # Agrupar níveis próximos
    def group_levels(levels, tolerance):
        if not levels:
            return []
        groups = []
        current_group = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - current_group[0]) <= tolerance:
                current_group.append(level)
            else:
                groups.append(sum(current_group) / len(current_group))
                current_group = [level]
        
        groups.append(sum(current_group) / len(current_group))
        return groups
    
    # Calcular tolerância baseada na volatilidade
    volatility = df['Close'].pct_change().std()
    tolerance = volatility * sensitivity
    
    # Agrupar níveis
    resistance_levels = group_levels(
        df[df['pivot_type'] == 'resistance']['High'].tolist(),
        tolerance
    )
    support_levels = group_levels(
        df[df['pivot_type'] == 'support']['Low'].tolist(),
        tolerance
    )
    
    return resistance_levels, support_levels

def executar_backtest(dados, params, capital_inicial):
    """Executa o backtesting da estratégia com parâmetros específicos"""
    df = dados.copy()
    
    # Inicializar variáveis
    capital = capital_inicial
    posicao = 0
    preco_entrada = 0
    operacoes = []
    
    # Detectar suportes e resistências
    resistance_levels, support_levels = detectar_suportes_resistencias(df)
    
    for i in range(1, len(df)):
        preco_atual = df['Close'].iloc[i]
        
        # Sinais de entrada
        sinal_compra = (
            df['RSI'].iloc[i] < params['rsi_oversold'] and 
            df['MACD'].iloc[i] > df['MACD_Signal'].iloc[i] and
            any(preco_atual > level for level in support_levels)
        )
        
        sinal_venda = (
            df['RSI'].iloc[i] > params['rsi_overbought'] and 
            df['MACD'].iloc[i] < df['MACD_Signal'].iloc[i] and
            any(preco_atual < level for level in resistance_levels)
        )
        
        # Verificar stop loss e take profit
        if posicao != 0:
            variacao = ((preco_atual - preco_entrada) / preco_entrada) * 100
            
            if (posicao == 1 and variacao <= -params['stop_loss']) or \
               (posicao == 1 and variacao >= params['take_profit']) or \
               (posicao == -1 and variacao >= params['stop_loss']) or \
               (posicao == -1 and variacao <= -params['take_profit']):
                
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
        if posicao == 0:
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

def calcular_metricas(operacoes, capital_inicial):
    """Calcula métricas de performance"""
    if len(operacoes) == 0:
        return {
            'retorno_total': 0,
            'num_operacoes': 0,
            'taxa_acerto': 0,
            'sharpe_ratio': 0
        }
    
    resultado_total = operacoes['resultado'].sum()
    retorno_total = (resultado_total / capital_inicial) * 100
    num_operacoes = len(operacoes[operacoes['tipo'].isin(['Compra', 'Venda'])])
    operacoes_lucrativas = len(operacoes[operacoes['resultado'] > 0])
    taxa_acerto = (operacoes_lucrativas / num_operacoes * 100) if num_operacoes > 0 else 0
    
    # Calcular Sharpe Ratio
    retornos_diarios = operacoes['resultado'].pct_change().dropna()
    sharpe_ratio = np.sqrt(252) * (retornos_diarios.mean() / retornos_diarios.std()) if len(retornos_diarios) > 0 else 0
    
    return {
        'retorno_total': retorno_total,
        'num_operacoes': num_operacoes,
        'taxa_acerto': taxa_acerto,
        'sharpe_ratio': sharpe_ratio
    }

def gerar_combinacoes():
    """Gera combinações aleatórias de parâmetros"""
    combinacoes = []
    for _ in range(num_combinacoes):
        params = {
            'rsi_period': np.random.randint(rsi_period_range[0], rsi_period_range[1] + 1),
            'rsi_overbought': np.random.randint(rsi_overbought_range[0], rsi_overbought_range[1] + 1),
            'rsi_oversold': np.random.randint(rsi_oversold_range[0], rsi_oversold_range[1] + 1),
            'macd_fast': np.random.randint(macd_fast_range[0], macd_fast_range[1] + 1),
            'macd_slow': np.random.randint(macd_slow_range[0], macd_slow_range[1] + 1),
            'macd_signal': np.random.randint(macd_signal_range[0], macd_signal_range[1] + 1),
            'stop_loss': np.random.uniform(stop_loss_range[0], stop_loss_range[1]),
            'take_profit': np.random.uniform(take_profit_range[0], take_profit_range[1])
        }
        combinacoes.append(params)
    return combinacoes

try:
    # Carregar dados
    with st.spinner('Carregando dados...'):
        dados = carregar_dados(acao_selecionada, periodo)
    
    # Botão para iniciar otimização
    if st.button("Iniciar Otimização"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Gerar combinações
        combinacoes = gerar_combinacoes()
        resultados = []
        
        # Executar backtesting para cada combinação
        for i, params in enumerate(combinacoes):
            status_text.text(f"Testando combinação {i+1}/{len(combinacoes)}")
            progress_bar.progress((i + 1) / len(combinacoes))
            
            # Calcular indicadores
            dados_com_indicadores = calcular_indicadores(dados, params)
            
            # Executar backtesting
            operacoes = executar_backtest(dados_com_indicadores, params, capital_inicial)
            
            # Calcular métricas
            metricas = calcular_metricas(operacoes, capital_inicial)
            
            # Adicionar resultados
            resultados.append({
                'params': params,
                'metricas': metricas
            })
        
        # Ordenar resultados por Sharpe Ratio
        resultados_ordenados = sorted(resultados, key=lambda x: x['metricas']['sharpe_ratio'], reverse=True)
        
        # Exibir melhores resultados
        st.subheader("Melhores Configurações")
        
        # Criar DataFrame com resultados
        df_resultados = pd.DataFrame([
            {
                'Retorno Total (%)': r['metricas']['retorno_total'],
                'Número de Operações': r['metricas']['num_operacoes'],
                'Taxa de Acerto (%)': r['metricas']['taxa_acerto'],
                'Sharpe Ratio': r['metricas']['sharpe_ratio'],
                'RSI Período': r['params']['rsi_period'],
                'RSI Sobrecompra': r['params']['rsi_overbought'],
                'RSI Sobrevenda': r['params']['rsi_oversold'],
                'MACD Rápido': r['params']['macd_fast'],
                'MACD Lento': r['params']['macd_slow'],
                'MACD Sinal': r['params']['macd_signal'],
                'Stop Loss (%)': r['params']['stop_loss'],
                'Take Profit (%)': r['params']['take_profit']
            }
            for r in resultados_ordenados[:10]
        ])
        
        st.dataframe(df_resultados)
        
        # Botão para salvar melhor configuração
        if st.button("Salvar Melhor Configuração"):
            melhor_config = {
                'acao': acao_selecionada,
                'periodo': periodo,
                'params': resultados_ordenados[0]['params'],
                'metricas': resultados_ordenados[0]['metricas'],
                'data_otimizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            configs = carregar_configuracoes()
            configs[f"{acao_selecionada}_{periodo}"] = melhor_config
            salvar_configuracoes(configs)
            
            st.success("Configuração salva com sucesso!")
        
        # Exibir configurações salvas
        st.subheader("Configurações Salvas")
        configs = carregar_configuracoes()
        if configs:
            for key, config in configs.items():
                with st.expander(f"Configuração para {key}"):
                    st.json(config)
        else:
            st.info("Nenhuma configuração salva ainda.")

except Exception as e:
    st.error(f"Erro ao executar otimização: {str(e)}") 