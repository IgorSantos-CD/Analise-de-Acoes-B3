import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import ta  # Biblioteca para indicadores técnicos
from plotly.subplots import make_subplots

st.set_page_config(page_title="Análise B3", layout="wide")

st.title("📈 Análise de Ações B3")

# Sidebar para seleção de ações
st.sidebar.header("Filtros")

# Lista de algumas ações populares da B3
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

# Seleção da ação
acao_selecionada = st.sidebar.selectbox(
    "Selecione uma ação:",
    options=list(acoes_populares.keys()),
    format_func=lambda x: f"{x} - {acoes_populares[x]}"
)

# Intervalo das velas
intervalo_velas = st.sidebar.selectbox(
    "Intervalo das velas:",
    options=['5m', '15m', '1h', '3h', '1d'],
    format_func=lambda x: {
        '5m': '5 Minutos',
        '15m': '15 Minutos',
        '1h': '1 Hora',
        '3h': '3 Horas',
        '1d': 'Diário'
    }[x]
)

# Definir períodos disponíveis baseado no intervalo
def get_periodos_disponiveis(intervalo):
    if intervalo == '5m':
        return ['1d', '5d', '1mo']
    elif intervalo == '15m':
        return ['1d', '5d', '1mo', '3mo']
    elif intervalo == '1h':
        return ['1d', '5d', '1mo', '3mo', '6mo']
    elif intervalo == '3h':
        return ['1d', '5d', '1mo', '3mo', '6mo', '1y']
    else:  # 1d
        return ['1mo', '3mo', '6mo', '1y', '2y', '5y']

# Período de análise
periodo = st.sidebar.selectbox(
    "Selecione o período de análise:",
    options=get_periodos_disponiveis(intervalo_velas),
    format_func=lambda x: {
        '1d': '1 Dia',
        '5d': '5 Dias',
        '1mo': '1 Mês',
        '3mo': '3 Meses',
        '6mo': '6 Meses',
        '1y': '1 Ano',
        '2y': '2 Anos',
        '5y': '5 Anos'
    }[x]
)

# Adicionar controles para indicadores técnicos no sidebar
st.sidebar.header("Indicadores Técnicos")

# Toggle para Médias Móveis
with st.sidebar.expander("📊 Médias Móveis", expanded=False):
    show_sma = st.checkbox("Média Móvel Simples (SMA)", value=True)
    show_ema = st.checkbox("Média Móvel Exponencial (EMA)", value=False)
    if show_sma or show_ema:
        if show_sma:
            sma_periods = st.multiselect(
                "Períodos SMA",
                options=[9, 20, 50, 100, 200],
                default=[20, 50]
            )
        if show_ema:
            ema_periods = st.multiselect(
                "Períodos EMA",
                options=[9, 20, 50, 100, 200],
                default=[20]
            )

# Toggle para Momentum
with st.sidebar.expander("📈 Momentum", expanded=False):
    show_rsi = st.checkbox("RSI", value=True)
    show_macd = st.checkbox("MACD", value=True)
    if show_rsi:
        rsi_period = st.slider("Período RSI", min_value=2, max_value=30, value=14)
        rsi_overbought = st.slider("Sobrecompra", min_value=50, max_value=100, value=70)
        rsi_oversold = st.slider("Sobrevenda", min_value=0, max_value=50, value=30)
    if show_macd:
        macd_fast = st.slider("MACD Rápido", min_value=5, max_value=20, value=12)
        macd_slow = st.slider("MACD Lento", min_value=20, max_value=40, value=26)
        macd_signal = st.slider("MACD Sinal", min_value=5, max_value=20, value=9)

# Toggle para Análise de Padrões
with st.sidebar.expander("🕯️ Padrões", expanded=False):
    show_patterns = st.checkbox("Padrões de Candlestick", value=True)
    show_sr = st.checkbox("Suportes e Resistências", value=True)
    if show_sr:
        sensitivity = st.slider(
            "Sensibilidade da Detecção",
            min_value=0.1,
            max_value=2.0,
            value=0.5,
            step=0.1,
            help="Ajusta a sensibilidade na detecção de níveis"
        )
        show_fibonacci = st.checkbox("Mostrar Níveis de Fibonacci", value=False)
        if show_fibonacci:
            fib_levels = st.multiselect(
                "Níveis de Fibonacci",
                options=[0, 0.236, 0.382, 0.5, 0.618, 0.786, 1],
                default=[0.236, 0.382, 0.5, 0.618],
                help="Selecione os níveis de Fibonacci para exibir"
            )

# Adicionar controles para ajuste do gráfico no sidebar
candle_width = 0.20  # Valor fixo para largura das velas
candle_spacing = 0.1  # Valor fixo para espaçamento entre velas

@st.cache_data
# Função para carregar dados das ações  
def carregar_dados(ticker, periodo, intervalo):
    acao = yf.Ticker(ticker)
    hist = acao.history(period=periodo, interval=intervalo)
    
    # Remove registros sem dados (mercado fechado)
    hist = hist.dropna()
    
    # Reindexa os dados para remover espaços entre os dias
    if intervalo == '1d':
        hist = hist.resample('D').last().dropna()
    elif intervalo in ['5m', '15m', '1h', '3h']:
        # Para intervalos intraday, mantém apenas os dias úteis
        hist = hist[hist.index.dayofweek < 5]  # Remove sábados e domingos
        hist = hist.between_time('10:00', '18:00')  # Mantém apenas horário de pregão
    
    return hist, acao.info

@st.cache_data
def calcular_indicadores(dados, show_sma, show_ema, show_rsi, show_macd, 
                        sma_periods, ema_periods, rsi_period, 
                        macd_fast, macd_slow, macd_signal):
    """Calcula os indicadores técnicos selecionados"""
    df = dados.copy()
    
    # Médias Móveis Simples
    if show_sma and sma_periods:
        for period in sma_periods:
            df[f'SMA_{period}'] = ta.trend.sma_indicator(df['Close'], window=period)
    
    # Médias Móveis Exponenciais
    if show_ema and ema_periods:
        for period in ema_periods:
            df[f'EMA_{period}'] = ta.trend.ema_indicator(df['Close'], window=period)
    
    # RSI
    if show_rsi:
        df['RSI'] = ta.momentum.rsi(df['Close'], window=rsi_period)
    
    # MACD
    if show_macd:
        macd = ta.trend.macd_diff(df['Close'], 
                                 window_slow=macd_slow,
                                 window_fast=macd_fast,
                                 window_sign=macd_signal)
        df['MACD'] = macd
        df['MACD_Signal'] = ta.trend.macd_signal(df['Close'],
                                                window_slow=macd_slow,
                                                window_fast=macd_fast,
                                                window_sign=macd_signal)
    
    return df

@st.cache_data
def detectar_padroes_candlestick(dados):
    """Detecta padrões de candlestick usando definições matemáticas rigorosas"""
    df = dados.copy()
    
    # Calculando médias móveis para contexto de tendência
    df['MM20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['MM50'] = ta.trend.sma_indicator(df['Close'], window=50)
    
    # Tendências
    df['tendencia_alta'] = df['MM20'] > df['MM50']
    df['tendencia_baixa'] = df['MM20'] < df['MM50']
    
    # Cálculos básicos para cada candle
    df['body'] = abs(df['Close'] - df['Open'])
    df['upper_wick'] = df.apply(lambda x: x['High'] - max(x['Open'], x['Close']), axis=1)
    df['lower_wick'] = df.apply(lambda x: min(x['Open'], x['Close']) - x['Low'], axis=1)
    df['range_total'] = df['High'] - df['Low']
    
    # Calculando percentis para definição de corpos longos e curtos
    corpo_70_percentil = df['body'].quantile(0.7)
    corpo_30_percentil = df['body'].quantile(0.3)
    
    # Doji
    df['doji'] = (
        (df['body'] <= 0.05 * df['range_total']) &  # Corpo muito pequeno
        (df['upper_wick'] >= 2 * df['body']) &      # Sombras significativas
        (df['lower_wick'] >= 2 * df['body'])
    )
    
    # Hammer (em tendência de baixa)
    df['hammer'] = (
        (df['lower_wick'] >= 2 * df['body']) &                          # Sombra inferior longa
        (df['upper_wick'] <= 0.1 * df['range_total']) &                # Sombra superior pequena
        (df.apply(lambda x: min(x['Open'], x['Close']) >               # Corpo na metade superior
                 (x['High'] + x['Low'])/2 - 0.3*(x['High'] - x['Low']), axis=1)) &
        df['tendencia_baixa'] &                                        # Confirmação de tendência
        df['Close'].shift(1).gt(df['Close'].shift(2))                 # Candle anterior mais baixo
    )
    
    # Shooting Star (em tendência de alta)
    df['shooting_star'] = (
        (df['upper_wick'] >= 2 * df['body']) &                         # Sombra superior longa
        (df['lower_wick'] <= 0.1 * df['range_total']) &               # Sombra inferior pequena
        (df.apply(lambda x: max(x['Open'], x['Close']) <              # Corpo na metade inferior
                 (x['High'] + x['Low'])/2 + 0.3*(x['High'] - x['Low']), axis=1)) &
        df['tendencia_alta']                                          # Em tendência de alta
    )
    
    # Marubozu (velas sem sombras)
    df['bullish_marubozu'] = (
        (df['Close'] > df['Open']) &                                   # Vela de alta
        (df['body'] > corpo_70_percentil) &                           # Corpo longo
        (df['upper_wick'] <= 0.05 * df['range_total']) &             # Sem sombras superiores
        (df['lower_wick'] <= 0.05 * df['range_total'])               # Sem sombras inferiores
    )
    
    df['bearish_marubozu'] = (
        (df['Close'] < df['Open']) &                                   # Vela de baixa
        (df['body'] > corpo_70_percentil) &                           # Corpo longo
        (df['upper_wick'] <= 0.05 * df['range_total']) &             # Sem sombras superiores
        (df['lower_wick'] <= 0.05 * df['range_total'])               # Sem sombras inferiores
    )
    
    # Spinning Top (removido pois era muito genérico)
    
    return df

@st.cache_data
def detectar_suportes_resistencias(dados, sensitivity=0.5):
    """Detecta níveis de suporte e resistência usando análise de pivots"""
    df = dados.copy()
    
    # Identificar pivots (pontos de reversão)
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
    
    # Agrupar níveis de suporte e resistência
    resistance_levels = group_levels(
        df[df['pivot_type'] == 'resistance']['High'].tolist(),
        tolerance
    )
    support_levels = group_levels(
        df[df['pivot_type'] == 'support']['Low'].tolist(),
        tolerance
    )
    
    # Obter preço atual
    preco_atual = df['Close'].iloc[-1]
    
    # Filtrar níveis baseado na posição do preço atual
    resistance_levels = [level for level in resistance_levels if level > preco_atual]
    support_levels = [level for level in support_levels if level < preco_atual]
    
    # Ordenar níveis por distância do preço atual
    def get_closest_levels(levels, preco, n=3):
        if not levels:
            return []
        # Ordenar níveis por distância do preço atual
        sorted_levels = sorted(levels, key=lambda x: abs(x - preco))
        return sorted_levels[:n]
    
    # Retornar apenas os 3 níveis mais próximos
    closest_resistance = get_closest_levels(resistance_levels, preco_atual)
    closest_support = get_closest_levels(support_levels, preco_atual)
    
    return closest_resistance, closest_support

@st.cache_data
def calcular_niveis_fibonacci(dados, fib_levels):
    """Calcula níveis de Fibonacci baseados no range de preços"""
    high = dados['High'].max()
    low = dados['Low'].min()
    diff = high - low
    
    fib_levels_dict = {}
    for level in fib_levels:
        if level == 0:
            fib_levels_dict[level] = low
        elif level == 1:
            fib_levels_dict[level] = high
        else:
            fib_levels_dict[level] = high - (diff * level)
    
    return fib_levels_dict

def analisar_momentum(dados, rsi_compra, rsi_venda, macd_fast, macd_slow):
    """Analisa sinais baseados em momentum"""
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

def analisar_price_action(dados):
    """Analisa padrões de price action"""
    df = dados.copy()
    
    # Detectar padrões
    df['doji'] = (abs(df['Close'] - df['Open']) <= 0.1 * (df['High'] - df['Low']))
    df['pin_bar'] = ((df['High'] - df['Low']) > 3 * abs(df['Close'] - df['Open']))
    
    return df

def analisar_tendencias(dados, mm_curta, mm_longa, atr_period):
    """Analisa tendências e volatilidade"""
    df = dados.copy()
    
    # Médias móveis
    df[f'MM{mm_curta}'] = ta.trend.sma_indicator(df['Close'], window=mm_curta)
    df[f'MM{mm_longa}'] = ta.trend.sma_indicator(df['Close'], window=mm_longa)
    
    # ATR para volatilidade
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], 
                                                window=atr_period)
    
    return df

def calcular_score_operacao(dados):
    """Calcula um score geral para operações"""
    score = 0
    
    # Momentum
    if dados['sinal_rsi'].iloc[-1] == 1 and dados['sinal_macd'].iloc[-1] == 1:
        score += 2
    elif dados['sinal_rsi'].iloc[-1] == -1 and dados['sinal_macd'].iloc[-1] == -1:
        score -= 2
    
    # Price Action
    if dados['doji'].iloc[-1]:
        score += 1 if dados['Close'].iloc[-1] > dados['Open'].iloc[-1] else -1
    
    # Tendência
    if dados['MM20'].iloc[-1] > dados['MM50'].iloc[-1]:
        score += 1
    else:
        score -= 1
    
    return score

def plotar_sinais(dados):
    """Cria um gráfico com todos os sinais"""
    # Verificar se há indicadores para mostrar
    tem_rsi = 'RSI' in dados.columns
    tem_macd = 'MACD' in dados.columns
    
    # Criar subplots apenas se houver indicadores
    if tem_rsi or tem_macd:
        fig = make_subplots(rows=3, cols=1, 
                           shared_xaxes=True,
                           vertical_spacing=0.05,
                           row_heights=[0.6, 0.2, 0.2])
    else:
        fig = go.Figure()
    
    # Gráfico principal
    fig.add_trace(go.Candlestick(
        x=dados.index,
        open=dados['Open'],
        high=dados['High'],
        low=dados['Low'],
        close=dados['Close'],
        name='Preço'
    ), row=1 if (tem_rsi or tem_macd) else None, col=1 if (tem_rsi or tem_macd) else None)
    
    # RSI
    if tem_rsi:
        fig.add_trace(go.Scatter(
            x=dados.index,
            y=dados['RSI'],
            name='RSI'
        ), row=2, col=1)
    
    # MACD
    if tem_macd:
        fig.add_trace(go.Scatter(
            x=dados.index,
            y=dados['MACD'],
            name='MACD'
        ), row=3, col=1)
    
    return fig

try:
    # Carregando dados
    with st.spinner('Carregando dados...'):
        dados, info = carregar_dados(acao_selecionada, periodo, intervalo_velas)
    
    # Inicializar variáveis para indicadores
    sma_periods = [] if not show_sma else sma_periods
    ema_periods = [] if not show_ema else ema_periods
    
    # Calculando indicadores apenas se algum estiver selecionado
    if show_sma or show_ema or show_rsi or show_macd:
        dados = calcular_indicadores(dados, show_sma, show_ema, show_rsi, show_macd,
                                   sma_periods, ema_periods, rsi_period,
                                   macd_fast, macd_slow, macd_signal)
    
    # Detectar padrões se estiver ativado
    if show_patterns:
        dados = detectar_padroes_candlestick(dados)
    
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

    # Criar gráfico principal
    fig = go.Figure()
    
    # Adicionar candlestick
    fig.add_trace(go.Candlestick(
        x=dados.index,
        open=dados['Open'],
        high=dados['High'],
        low=dados['Low'],
        close=dados['Close'],
        name='OHLC',
        text=[f"Data: {index}<br>" +
              f"Abertura: R$ {open:.2f}<br>" +
              f"Máxima: R$ {high:.2f}<br>" +
              f"Mínima: R$ {low:.2f}<br>" +
              f"Fechamento: R$ {close:.2f}"
              for index, open, high, low, close in zip(
                  dados.index,
                  dados['Open'],
                  dados['High'],
                  dados['Low'],
                  dados['Close']
              )],
        hoverinfo='text',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
        increasing_fillcolor='#26a69a',
        decreasing_fillcolor='#ef5350',
        line=dict(width=1),
        whiskerwidth=candle_width,
        xperiodalignment="middle",
        xperiod=candle_spacing
    ))
    
    # Adicionando médias móveis apenas se estiverem disponíveis
    if show_sma and sma_periods:
        for period in sma_periods:
            if f'SMA_{period}' in dados.columns:
                fig.add_trace(go.Scatter(
                    x=dados.index,
                    y=dados[f'SMA_{period}'],
                    name=f'SMA {period}',
                    line=dict(width=1),
                    opacity=0.7
                ))
    
    if show_ema and ema_periods:
        for period in ema_periods:
            if f'EMA_{period}' in dados.columns:
                fig.add_trace(go.Scatter(
                    x=dados.index,
                    y=dados[f'EMA_{period}'],
                    name=f'EMA {period}',
                    line=dict(width=1, dash='dash'),
                    opacity=0.7
                ))

    # Adicionar suportes e resistências ao gráfico apenas se estiverem disponíveis
    if show_sr:
        try:
            resistance_levels, support_levels = detectar_suportes_resistencias(dados, sensitivity)
            
            # Plotar níveis de resistência
            for level in resistance_levels:
                fig.add_hline(
                    y=level,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"R: {level:.2f}",
                    annotation_position="right",
                    annotation_font_color="red"
                )
            
            # Plotar níveis de suporte
            for level in support_levels:
                fig.add_hline(
                    y=level,
                    line_dash="dash",
                    line_color="green",
                    annotation_text=f"S: {level:.2f}",
                    annotation_position="right",
                    annotation_font_color="green"
                )
            
            # Adicionar níveis de Fibonacci apenas se explicitamente ativado
            if show_fibonacci and 'fib_levels' in locals():
                fib_levels_dict = calcular_niveis_fibonacci(dados, fib_levels)
                
                for level, price in fib_levels_dict.items():
                    fig.add_hline(
                        y=price,
                        line_dash="dot",
                        line_color="yellow",
                        annotation_text=f"Fib {level:.3f}: {price:.2f}",
                        annotation_position="right",
                        annotation_font_color="yellow"
                    )
        except Exception as e:
            st.warning(f"Não foi possível calcular suportes e resistências: {str(e)}")
    
    # Detectar padrões se estiver ativado
    if show_patterns:
        # Adicionar marcadores para os padrões
        for idx in dados.index:
            if dados.loc[idx, 'doji']:
                fig.add_trace(go.Scatter(
                    x=[idx],
                    y=[dados.loc[idx, 'High']],
                    mode='markers+text',
                    marker=dict(
                        symbol='diamond',
                        size=10,
                        color='yellow',
                        line=dict(color='black', width=1)
                    ),
                    text='D',
                    textposition='top center',
                    name='Doji',
                    showlegend=False
                ))
            if dados.loc[idx, 'hammer']:
                fig.add_trace(go.Scatter(
                    x=[idx],
                    y=[dados.loc[idx, 'Low']],
                    mode='markers+text',
                    marker=dict(
                        symbol='triangle-up',
                        size=10,
                        color='green',
                        line=dict(color='black', width=1)
                    ),
                    text='H',
                    textposition='bottom center',
                    name='Hammer',
                    showlegend=False
                ))
            if dados.loc[idx, 'shooting_star']:
                fig.add_trace(go.Scatter(
                    x=[idx],
                    y=[dados.loc[idx, 'High']],
                    mode='markers+text',
                    marker=dict(
                        symbol='triangle-down',
                        size=10,
                        color='red',
                        line=dict(color='black', width=1)
                    ),
                    text='SS',
                    textposition='top center',
                    name='Shooting Star',
                    showlegend=False
                ))
            if dados.loc[idx, 'bullish_marubozu']:
                fig.add_trace(go.Scatter(
                    x=[idx],
                    y=[dados.loc[idx, 'High']],
                    mode='markers+text',
                    marker=dict(
                        symbol='circle',
                        size=10,
                        color='green',
                        line=dict(color='black', width=1)
                    ),
                    text='BM',
                    textposition='top center',
                    name='Bullish Marubozu',
                    showlegend=False
                ))
            if dados.loc[idx, 'bearish_marubozu']:
                fig.add_trace(go.Scatter(
                    x=[idx],
                    y=[dados.loc[idx, 'Low']],
                    mode='markers+text',
                    marker=dict(
                        symbol='circle',
                        size=10,
                        color='red',
                        line=dict(color='black', width=1)
                    ),
                    text='BM',
                    textposition='bottom center',
                    name='Bearish Marubozu',
                    showlegend=False
                ))
    
        # Adicionar legenda para os padrões
        st.subheader("Padrões de Candlestick Detectados")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Padrões de Reversão**")
            st.markdown("🔷 D - Doji: Indica indecisão e possível reversão")
            st.markdown("🔼 H - Hammer: Possível reversão de alta")
            st.markdown("🔽 SS - Shooting Star: Possível reversão de baixa")
        
        with col2:
            st.markdown("**Padrões de Continuidade**")
            st.markdown("🟢 BM - Bullish Marubozu: Forte tendência de alta")
            st.markdown("🔴 BM - Bearish Marubozu: Forte tendência de baixa")
        
        with col3:
            st.markdown("**Padrões de Indecisão**")
            st.markdown("⬜ D - Doji: Indica indecisão e possível reversão")
            st.markdown("🔼 H - Hammer: Possível reversão de alta")
            st.markdown("🔽 SS - Shooting Star: Possível reversão de baixa")
    
    # Layout do gráfico principal
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=True,
        height=600,
        dragmode='pan',
        xaxis=dict(
            type='date',
            rangeslider=dict(
                visible=True,
                thickness=0.05,
                bgcolor="rgb(48, 48, 48)",
                bordercolor="rgb(128, 128, 128)",
                borderwidth=1,
                range=[dados.index[-min(100, len(dados))].timestamp() * 1000, dados.index[-1].timestamp() * 1000]  # Zoom padrão do rangeslider
            ),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1D", step="day", stepmode="backward"),
                    dict(count=7, label="7D", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1A", step="year", stepmode="backward"),
                    dict(step="all", label="Tudo")
                ]),
                font=dict(color="white"),
                bgcolor="rgb(48, 48, 48)",
                activecolor="rgb(65, 65, 65)"
            )
        ),
        yaxis=dict(
            title="Preço (R$)",
            tickformat='.2f',
            tickprefix='R$ ',
            fixedrange=False,
            side='right'
        ),
        xaxis_gridcolor='rgba(128, 128, 128, 0.1)',
        yaxis_gridcolor='rgba(128, 128, 128, 0.1)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0, 0, 0, 0.5)",
            bordercolor="rgba(128, 128, 128, 0.5)",
            borderwidth=1
        ),
        bargap=0.15,
        bargroupgap=0.1
    )
    
    # Configurações do gráfico
    config = {
        'modeBarButtonsToAdd': [
            'drawline',
            'drawopenpath',
            'drawclosedpath',
            'drawcircle',
            'drawrect',
            'eraseshape'
        ],
        'modeBarButtons': [
            ['zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
            ['toImage'],
            ['zoom3d', 'pan3d', 'resetCameraDefault3d', 'resetCameraLastSave3d'],
            ['hoverClosestCartesian', 'hoverCompareCartesian']
        ],
        'scrollZoom': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'{acao_selecionada}_chart',
            'height': 600,
            'width': 1200,
            'scale': 2
        },
        'displayModeBar': True,
        'doubleClick': 'reset+autosize'
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)
    
    # Gráficos adicionais para RSI e MACD
    if show_rsi or show_macd:
        col1, col2 = st.columns(2)
        
        if show_rsi and 'RSI' in dados.columns:
            with col1:
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(
                    x=dados.index,
                    y=dados['RSI'],
                    name='RSI',
                    line=dict(color='blue')
                ))
                fig_rsi.add_hline(y=rsi_overbought, line_dash="dash", line_color="red")
                fig_rsi.add_hline(y=rsi_oversold, line_dash="dash", line_color="green")
                fig_rsi.update_layout(
                    title='RSI',
                    height=300,
                    template='plotly_dark',
                    yaxis=dict(range=[0, 100])
                )
                st.plotly_chart(fig_rsi, use_container_width=True)
        
        if show_macd and 'MACD' in dados.columns:
            with col2:
                fig_macd = go.Figure()
                fig_macd.add_trace(go.Scatter(
                    x=dados.index,
                    y=dados['MACD'],
                    name='MACD',
                    line=dict(color='blue')
                ))
                fig_macd.add_trace(go.Scatter(
                    x=dados.index,
                    y=dados['MACD_Signal'],
                    name='Sinal',
                    line=dict(color='orange')
                ))
                fig_macd.update_layout(
                    title='MACD',
                    height=300,
                    template='plotly_dark'
                )
                st.plotly_chart(fig_macd, use_container_width=True)

    # Volume
    st.subheader("Volume de Negociação")
    fig_volume = go.Figure(data=[
        go.Bar(
            x=dados.index, 
            y=dados['Volume'],
            name='Volume',
            hovertemplate=
            "<b>Data</b>: %{x}<br>" +
            "<b>Volume</b>: %{y:,.0f}<br>" +
            "<extra></extra>"
        )
    ])
    
    fig_volume.update_layout(
        template='plotly_dark',
        height=250,
        xaxis_rangeslider_visible=False,
        yaxis=dict(title="Volume"),
        xaxis_gridcolor='rgba(128, 128, 128, 0.1)',
        yaxis_gridcolor='rgba(128, 128, 128, 0.1)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=50, r=50, t=50, b=50),
    )
    
    st.plotly_chart(fig_volume, use_container_width=True, config={'displaylogo': False})

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