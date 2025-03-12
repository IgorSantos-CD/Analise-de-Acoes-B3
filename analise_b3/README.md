# Análise de Ações B3

Uma aplicação web interativa para análise de ações da B3 (Bolsa de Valores do Brasil) utilizando Python e Streamlit.

## Funcionalidades

- Visualização de dados históricos de ações
- Gráfico de Candlestick
- Análise de volume de negociação
- Métricas importantes (preço atual, variação, máximas e mínimas)
- Análise de retornos e volatilidade

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone este repositório ou baixe os arquivos
2. Navegue até o diretório do projeto
3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como Usar

1. No diretório do projeto, execute:
```bash
streamlit run app.py
```

2. A aplicação abrirá automaticamente no seu navegador padrão
3. Selecione a ação desejada no menu lateral
4. Escolha o período de análise

## Dados

Os dados são obtidos em tempo real através da API do Yahoo Finance (yfinance).
Note que pode haver um pequeno atraso nos dados em relação ao mercado real.

## Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests. 