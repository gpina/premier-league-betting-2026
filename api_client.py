import pandas as pd
import requests
import io

class FootballDataClient:
    """
    Cliente para obter dados GRATUITOS do football-data.co.uk (CSV).
    """
    def __init__(self):
        # URL da época atual 2025/2026
        self.url_atual = "https://www.football-data.co.uk/mmz4281/2526/E0.csv"
        # Mapeamento de nomes para o motor (O CSV usa siglas às vezes, mas Premier League é ok)
        self.column_map = {
            'Date': 'data',
            'HomeTeam': 'casa',
            'AwayTeam': 'fora',
            'FTHG': 'golos_casa',
            'FTAG': 'golos_fora',
            'HST': 'remates_baliza_casa',
            'AST': 'remates_baliza_fora',
            'HC': 'cantos_casa',
            'AC': 'cantos_fora',
            'B365H': 'odd_casa',
            'B365D': 'odd_empate',
            'B365A': 'odd_fora',
            'B365>2.5': 'odd_over_25',
            'B365<2.5': 'odd_under_25'
        }

    def carregar_resultados_recentes(self):
        """Baixa o CSV e retorna os resultados mais recentes."""
        try:
            # Simulando o download do CSV
            response = requests.get(self.url_atual)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
            
            # Limpeza e Seleção
            df = df[self.column_map.keys()].rename(columns=self.column_map)
            df['data'] = pd.to_datetime(df['data'], dayfirst=True)
            return df.sort_values(by='data', ascending=False)
        except Exception as e:
            print(f"Erro ao carregar CSV gratuito: {e}")
            return pd.DataFrame()

    def get_live_odds(self, api_key):
        """
        Busca odds reais da 'The Odds API' para a Premier League.
        """
        if not api_key: return []
        
        url = f"https://api.the-odds-api.com/v4/sports/soccer_england_league1/odds/" # Lembrete: Premier League pode ser 'soccer_epl' ou similar
        params = {
            'apiKey': api_key,
            'regions': 'eu', # Europa
            'markets': 'h2h,totals,btts',
            'oddsFormat': 'decimal'
        }
        
        try:
            # Nota: Corrigir o sport key para 'soccer_epl'
            url = url.replace('soccer_england_league1', 'soccer_epl')
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erro ao buscar odds ao vivo: {e}")
            return []

    def get_mock_next_fixtures(self, live_data=None):
        """
        Retorna os próximos jogos. Se live_data (da API) existir, converte-o.
        """
        if live_data:
            fixtures = []
            for match in live_data[:10]: # Limitar aos próximos 10
                # Extrair odds do primeiro bookmaker (ex: Bet365 ou Avg)
                h2h = next((m for m in match['bookmakers'] if m['key'] == 'bet365'), match['bookmakers'][0])
                odds = h2h['markets'][0]['outcomes']
                
                fixtures.append({
                    "data": match['commence_time'].split('T')[0],
                    "casa": match['home_team'],
                    "fora": match['away_team'],
                    "odd": next(o['price'] for o in odds if o['name'] == match['home_team'])
                })
            return fixtures

        # Fallback para Mock se a API falhar ou não houver chave
        return [
            {"data": "2026-04-10", "casa": "West Ham", "fora": "Wolverhampton", "odd": 2.10},
            {"data": "2026-04-11", "casa": "Arsenal", "fora": "Bournemouth", "odd": 1.35},
            {"data": "2026-04-11", "casa": "Brentford", "fora": "Everton", "odd": 1.95},
            {"data": "2026-04-11", "casa": "Burnley", "fora": "Brighton", "odd": 3.10},
            {"data": "2026-04-11", "casa": "Liverpool", "fora": "Fulham", "odd": 1.40},
            {"data": "2026-04-12", "casa": "Sunderland", "fora": "Tottenham", "odd": 4.50},
            {"data": "2026-04-12", "casa": "Nottingham Forest", "fora": "Aston Villa", "odd": 2.80},
            {"data": "2026-04-12", "casa": "Crystal Palace", "fora": "Newcastle", "odd": 2.60},
            {"data": "2026-04-12", "casa": "Chelsea", "fora": "Manchester City", "odd": 3.40},
            {"data": "2026-04-13", "casa": "Manchester United", "fora": "Leeds United", "odd": 1.65}
        ]
