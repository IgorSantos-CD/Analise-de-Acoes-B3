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
    options=['5m', '15m', '1h', '3h', '1d'],
    format_func=lambda x: {
        '5m': '5 Minutos',
        '15m': '15 Minutos',
        '1h': '1 Hora',
        '3h': '3 Horas',
        '1d': 'Diário'
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
        '5m': 'Cinco Minutos',
        '15m': 'Quinze Minutos',
        '1h': 'Uma Hora',
        '3h': 'Três Horas',
        '1d': 'Diário'
    }
    st.subheader(f"Gráfico de Candlestick ({intervalo_nome[intervalo_velas]})")
    fig = go.Figure(data=[go.Candlestick(
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
                hoverinfo='text'
    )])
    
    # Configuração do layout melhorado
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=True,  # Habilitando o rangeslider
        height=600,
        dragmode='pan',  # Alterado para pan (arrastar) como padrão
        xaxis=dict(
            type='date',
            rangeslider=dict(visible=True, thickness=0.05),
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
            fixedrange=False  # Permite zoom no eixo Y
        ),
        # Adicionando uma grade mais suave
        xaxis_gridcolor='rgba(128, 128, 128, 0.1)',
        yaxis_gridcolor='rgba(128, 128, 128, 0.1)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        # Configurando as margens
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=True,  # Mostra a legenda
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        # Adicionando botões de modo de interação
        modebar_add=[
            'drawline',
            'drawopenpath',
            'drawclosedpath',
            'drawcircle',
            'drawrect',
            'eraseshape'
        ]
    )

    # Configurações adicionais para melhor interatividade
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
        'displayModeBar': True,  # Sempre mostra a barra de ferramentas
        'doubleClick': 'reset+autosize'  # Duplo clique reseta o zoom
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)

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

    # Volume com melhorias visuais também
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