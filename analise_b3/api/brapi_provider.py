import requests
import pandas as pd
from datetime import datetime
import streamlit as st

class BrapiProvider:
    def __init__(self):
        self.base_url = "https://brapi.dev/api"
        self.token = st.secrets.get("BRAPI_TOKEN", "")  # Token será armazenado nas secrets do Streamlit
    
    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Faz uma requisição para a API"""
        if params is None:
            params = {}
        
        # Adiciona o token aos parâmetros
        params['token'] = self.token
        
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erro na API: {response.status_code} - {response.text}")
    
    def get_stock_data(self, symbol: str, range: str = "1d") -> pd.DataFrame:
        """
        Obtém dados históricos de uma ação
        range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        """
        endpoint = f"/quote/{symbol}"
        params = {'range': range, 'interval': '1d'}  # Podemos ajustar o intervalo conforme necessário
        
        try:
            data = self._make_request(endpoint, params)
            
            if 'results' in data and len(data['results']) > 0:
                stock_data = data['results'][0]
                
                # Converte os dados para DataFrame
                if 'historicalDataPrice' in stock_data:
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
                    
                    return df
                
            raise Exception("Dados não encontrados")
            
        except Exception as e:
            raise Exception(f"Erro ao obter dados da ação: {str(e)}")
    
    def get_available_stocks(self) -> dict:
        """Obtém lista de ações disponíveis"""
        try:
            data = self._make_request("/available")
            
            stocks = {}
            if 'stocks' in data:
                for stock in data['stocks']:
                    symbol = stock['stock']
                    name = stock.get('name', symbol)
                    stocks[symbol] = name
            
            return stocks
            
        except Exception as e:
            # Fallback para lista básica em caso de erro
            return {
                'PETR4': 'Petrobras PN',
                'VALE3': 'Vale ON',
                'ITUB4': 'Itaú PN',
                'BBDC4': 'Bradesco PN',
                'ABEV3': 'Ambev ON',
                'MGLU3': 'Magazine Luiza ON',
                'WEGE3': 'WEG ON'
            } 