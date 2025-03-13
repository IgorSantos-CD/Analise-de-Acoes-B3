import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import ta  # Biblioteca para indicadores técnicos

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
    options=['5m', '15m', '1h', '3h', '1d'],
    format_func=lambda x: {
        '5m': '5 Minutos',
        '15m': '15 Minutos',
        '1h': '1 Hora',
        '3h': '3 Horas',
        '1d': 'Diário'
    }[x]
)

# Adicionar controles para indicadores técnicos no sidebar
st.sidebar.header("Indicadores Técnicos")
show_sma = st.sidebar.checkbox("Média Móvel Simples (SMA)", value=True)
show_ema = st.sidebar.checkbox("Média Móvel Exponencial (EMA)", value=False)
show_rsi = st.sidebar.checkbox("RSI", value=False)
show_macd = st.sidebar.checkbox("MACD", value=False)

# Períodos para as médias móveis
sma_periods = []
ema_periods = []
if show_sma or show_ema:
    st.sidebar.subheader("Períodos das Médias Móveis")
    if show_sma:
        sma_periods = st.sidebar.multiselect(
            "Períodos SMA",
            options=[9, 20, 50, 100, 200],
            default=[20, 50]
        )
    if show_ema:
        ema_periods = st.sidebar.multiselect(
            "Períodos EMA",
            options=[9, 20, 50, 100, 200],
            default=[20]
        )

# Configurações do RSI
rsi_period = 14
rsi_overbought = 70
rsi_oversold = 30
if show_rsi:
    st.sidebar.subheader("Configurações do RSI")
    rsi_period = st.sidebar.slider("Período RSI", min_value=2, max_value=30, value=14)
    rsi_overbought = st.sidebar.slider("Sobrecompra", min_value=50, max_value=100, value=70)
    rsi_oversold = st.sidebar.slider("Sobrevenda", min_value=0, max_value=50, value=30)

# Configurações do MACD
macd_fast = 12
macd_slow = 26
macd_signal = 9
if show_macd:
    st.sidebar.subheader("Configurações do MACD")
    macd_fast = st.sidebar.slider("MACD Rápido", min_value=5, max_value=20, value=12)
    macd_slow = st.sidebar.slider("MACD Lento", min_value=20, max_value=40, value=26)
    macd_signal = st.sidebar.slider("MACD Sinal", min_value=5, max_value=20, value=9)

# Adicionar controles para padrões de candlestick no sidebar
st.sidebar.header("Padrões de Candlestick")
show_patterns = st.sidebar.checkbox("Mostrar Padrões de Candlestick", value=True)

# Adicionar controles para ajuste do gráfico no sidebar
st.sidebar.header("Ajustes do Gráfico")
candle_width = st.sidebar.slider(
    "Largura das Velas",
    min_value=0.1,
    max_value=0.8,
    value=0.4,
    step=0.05,
    help="Ajusta a largura das velas no gráfico"
)

candle_spacing = st.sidebar.slider(
    "Espaçamento entre Velas",
    min_value=0.0,
    max_value=0.3,
    value=0.05,
    step=0.01,
    help="Ajusta o espaçamento entre as velas"
)

@st.cache_data
# Função para carregar dados das ações  
def carregar_dados(ticker, periodo, intervalo):
    acao = yf.Ticker(ticker)
    hist = acao.history(period=periodo, interval=intervalo)
    return hist, acao.info

@st.cache_data
def calcular_indicadores(dados, show_sma, show_ema, show_rsi, show_macd, 
                        sma_periods, ema_periods, rsi_period, 
                        macd_fast, macd_slow, macd_signal):
    """Calcula os indicadores técnicos selecionados"""
    df = dados.copy()
    
    # Médias Móveis Simples
    if show_sma:
        for period in sma_periods:
            df[f'SMA_{period}'] = ta.trend.sma_indicator(df['Close'], window=period)
    
    # Médias Móveis Exponenciais
    if show_ema:
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

try:
    # Carregando dados
    with st.spinner('Carregando dados...'):
        dados, info = carregar_dados(acao_selecionada, periodo, intervalo_velas)
        
    # Calculando indicadores
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

    # Gráfico de candlestick com indicadores
    fig = go.Figure()
    
    # Candlestick principal
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
    
    # Adicionando médias móveis
    if show_sma:
        for period in sma_periods:
            fig.add_trace(go.Scatter(
                x=dados.index,
                y=dados[f'SMA_{period}'],
                name=f'SMA {period}',
                line=dict(width=1),
                opacity=0.7
            ))
    
    if show_ema:
        for period in ema_periods:
            fig.add_trace(go.Scatter(
                x=dados.index,
                y=dados[f'EMA_{period}'],
                name=f'EMA {period}',
                line=dict(width=1, dash='dash'),
                opacity=0.7
            ))
    
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
                borderwidth=1
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
        
        if show_rsi:
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
        
        if show_macd:
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