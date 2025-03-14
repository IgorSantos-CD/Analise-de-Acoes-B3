import streamlit as st
import pandas as pd
import requests
from datetime import datetime

class BrapiProvider:
    def __init__(self):
        """Inicializa o provedor de dados da BRAPI"""
        self.base_url = "https://brapi.dev/api/quote"
        self.token = st.secrets["BRAPI_TOKEN"]
        
    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Faz uma requisição para a API da BRAPI"""
        if params is None:
            params = {}
            
        params['token'] = self.token
        
        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()  # Levanta exceção para status codes de erro
            return response.json()
        except requests.exceptions.RequestException as e:
            if "429" in str(e):
                raise Exception("Limite de requisições atingido. Tente novamente mais tarde.")
            raise Exception(f"Erro na requisição: {str(e)}")
    
    def get_stock_data(self, symbol: str, range: str = "1d") -> pd.DataFrame:
        """
        Obtém dados históricos de uma ação
        range: 1d, 5d, 1mo, 3mo (limite do plano gratuito)
        """
        endpoint = f"/{symbol}"
        params = {'range': range, 'interval': '1d'}
        
        try:
            data = self._make_request(endpoint, params)
            
            if not data.get('results'):
                raise Exception(f"Dados não encontrados para {symbol}")
                
            stock_data = data['results'][0]
            
            if not stock_data.get('historicalDataPrice'):
                raise Exception(f"Dados históricos não disponíveis para {symbol}")
                
            df = pd.DataFrame(stock_data['historicalDataPrice'])
            
            # Converte a coluna date para datetime
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # Renomeia as colunas para o padrão que usamos
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            # Ordena o índice em ordem crescente
            df = df.sort_index()
            
            return df
            
        except Exception as e:
            raise Exception(f"Erro ao obter dados da ação {symbol}: {str(e)}")
            
    def get_available_stocks(self) -> dict:
        """Retorna um dicionário com as ações disponíveis"""
        try:
            endpoint = "/available"
            data = self._make_request(endpoint)
            
            if not data.get('stocks'):
                raise Exception("Lista de ações não disponível")
                
            # Cria um dicionário com símbolo -> nome
            stocks_dict = {}
            for stock in data['stocks']:
                symbol = stock.get('stock')
                name = stock.get('name')
                if symbol and name:
                    stocks_dict[symbol] = name
                    
            return stocks_dict
            
        except Exception as e:
            raise Exception(f"Erro ao obter lista de ações: {str(e)}") 