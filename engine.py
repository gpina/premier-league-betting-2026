import pandas as pd
import numpy as np
from scipy.stats import poisson
from ai_service import AIService
from database import Database

class EngineAprendizagem:
    def __init__(self, data_path='E0.csv'):
        self.db = Database()
        self.df = pd.read_csv(data_path)
        self.df['Date'] = pd.to_datetime(self.df['Date'], dayfirst=True)
        self.ai = AIService()
        
        # Normalização de nomes (Mapeamento de variações comuns)
        self.team_map = {
            "Arsenal FC": "Arsenal",
            "Chelsea FC": "Chelsea",
            "Manchester City FC": "Man City",
            "Man City": "Man City",
            "Manchester United FC": "Man United",
            "Man United": "Man United",
            "Tottenham Hotspur FC": "Tottenham",
            "Newcastle United FC": "Newcastle",
            "Aston Villa FC": "Aston Villa",
            "Liverpool FC": "Liverpool"
        }
        
        # Carregar Ratings (ELO/Força) do DB
        self.ratings = self.db.carregar_ratings()
        
        # Se o DB estiver vazio, inicializar com 1.0 para todos
        all_teams = pd.concat([self.df['HomeTeam'], self.df['AwayTeam']]).unique()
        for team in all_teams:
            if team not in self.ratings:
                self.ratings[team] = 1.0
                
        self._preparar_modelo_poisson()

    def _preparar_modelo_poisson(self):
        # Cálculos de força baseados em gols para Poisson
        all_teams = pd.concat([self.df['HomeTeam'], self.df['AwayTeam']]).unique()
        self.team_stats = {}
        for team in all_teams:
            home_games = self.df[self.df['HomeTeam'] == team]
            away_games = self.df[self.df['AwayTeam'] == team]
            self.team_stats[team] = {
                'ataque_home': home_games['FTHG'].mean() if len(home_games) > 0 else 1.0,
                'defesa_home': home_games['FTAG'].mean() if len(home_games) > 0 else 1.2,
                'ataque_away': away_games['FTAG'].mean() if len(away_games) > 0 else 0.8,
                'defesa_away': away_games['FTHG'].mean() if len(away_games) > 0 else 1.5
            }
        self.media_gols_home = self.df['FTHG'].mean()
        self.media_gols_away = self.df['FTAG'].mean()

    def _get_team_stats(self, team):
        # Aplica normalização técnica
        team = self.team_map.get(team, team)
        # Retorna estatísticas base ou defaults se o time não existir no CSV
        default = {'ataque_home': 1.0, 'defesa_home': 1.2, 'ataque_away': 0.8, 'defesa_away': 1.5}
        return self.team_stats.get(team, default)

    def calcular_probabilidade(self, casa, fora, fadiga_casa=False, fadiga_fora=False):
        casa = self.team_map.get(casa, casa)
        fora = self.team_map.get(fora, fora)
        
        # Combina o Rating (Aprendizagem) com Poisson (Estatística)
        rating_casa = self.ratings.get(casa, 1.0)
        rating_fora = self.ratings.get(fora, 1.0)
        
        # Ajuste de Fadiga
        if fadiga_casa: rating_casa *= 0.90
        if fadiga_fora: rating_fora *= 0.90
        
        stats_casa = self._get_team_stats(casa)
        stats_fora = self._get_team_stats(fora)
        
        # Cálculo Poisson Base
        lambda_home = (stats_casa['ataque_home'] * stats_fora['defesa_away']) / self.media_gols_home
        lambda_away = (stats_fora['ataque_away'] * stats_casa['defesa_home']) / self.media_gols_away
        
        prob_matrix = np.outer(poisson.pmf(range(7), lambda_home), poisson.pmf(range(7), lambda_away))
        p_home_poisson = np.sum(np.triu(prob_matrix, 1).T)
        
        # Média ponderada entre Rating (ELO) e Poisson
        diff = (rating_casa - rating_fora) * 0.2
        prob_final = p_home_poisson + diff
        
        return min(0.95, max(0.05, prob_final))

    def calcular_mercados_adicionais(self, casa, fora, fadiga_casa=False, fadiga_fora=False):
        stats_casa = self._get_team_stats(casa)
        stats_fora = self._get_team_stats(fora)
        
        lambda_home = (stats_casa['ataque_home'] * stats_fora['defesa_away']) / self.media_gols_home
        lambda_away = (stats_fora['ataque_away'] * stats_casa['defesa_home']) / self.media_gols_away
        
        # Ajuste por Fadiga nos gols esperados
        if fadiga_casa: lambda_home *= 0.9
        if fadiga_fora: lambda_away *= 0.9
        
        prob_matrix = np.outer(poisson.pmf(range(7), lambda_home), poisson.pmf(range(7), lambda_away))
        
        p_over25 = 1 - np.sum(np.array([prob_matrix[i,j] for i in range(7) for j in range(7) if i+j <= 2]))
        p_btts = sum(prob_matrix[i, j] for i in range(1, 7) for j in range(1, 7))
        
        return p_over25, p_btts

    def atualizar_ratings_resultado(self, casa, fora, p_ia, res_real, k=0.1):
        # Aprendizagem por reforço (Simples)
        erro = res_real - p_ia
        self.ratings[casa] += k * erro
        self.ratings[fora] -= k * erro
        return erro ** 2 # Brier Score parcial

    def get_ev(self, prob_ia, odd_mercado):
        if odd_mercado <= 0: return 0
        return (prob_ia * odd_mercado) - 1

    def calcular_kelly(self, prob, odd, banca, risco_max):
        if odd <= 1: return 0, 0
        q = 1 - prob
        kelly = (prob * (odd - 1) - q) / (odd - 1)
        # Kelly Fracionário (50%) e limitado pelo risco máximo
        kelly_frat = max(0, kelly * 0.5)
        kelly_safe = min(kelly_frat, risco_max / 100)
        return kelly_safe * banca, kelly_safe

    def gerar_recomendacoes(self, fixture, use_ai=False):
        casa, fora = fixture['Home'], fixture['Away']
        # Usar as funções internas que o app também usa
        p_home = self.calcular_probabilidade(casa, fora)
        p_over, p_btts = self.calcular_mercados_adicionais(casa, fora)
        
        ai_insight = None
        if use_ai:
            ai_insight = self.ai.analise_partida(casa, fora)
            adj = (ai_insight['sentimento'] * 0.08)
            p_home = min(0.99, max(0.01, p_home + adj))
        
        recoms = []
        # Limiar mais rigido para Vencedor (Principal)
        # Só recomenda se a probabilidade for alta E houver vantagem clara
        if p_home > 0.68: recoms.append({'mercado': 'Vencedor: ' + casa, 'confianca': p_home, 'tipo': 'Principal'})
        elif p_home < 0.28: recoms.append({'mercado': 'Vencedor: ' + fora, 'confianca': 1-p_home, 'tipo': 'Principal'})
        
        if p_btts > 0.66: recoms.append({'mercado': 'Ambas Marcam: Sim', 'confianca': p_btts, 'tipo': 'Golos'})
        if p_over > 0.68: recoms.append({'mercado': 'Over 2.5 Gols', 'confianca': p_over, 'tipo': 'Golos'})
        
        return recoms, ai_insight
