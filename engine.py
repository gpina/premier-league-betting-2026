import pandas as pd
import numpy as np
from scipy.stats import poisson
from ai_service import AIService
from database import Database

class EngineAprendizagem:
    def __init__(self, data_path='E0.csv', h_path='E0_5y.csv'):
        self.db = Database()
        self.ai = AIService()
        
        # Carregar Dados Atuais
        self.df = pd.read_csv(data_path)
        self.df['Date'] = pd.to_datetime(self.df['Date'], dayfirst=True)
        
        # Carregar Histórico de 5 Anos
        try:
            self.df_h = pd.read_csv(h_path)
            self.df_h['Date'] = pd.to_datetime(self.df_h['Date'], dayfirst=True)
        except:
            self.df_h = self.df.copy() # Fallback

        self.team_map = {
            "Arsenal FC": "Arsenal", "Chelsea FC": "Chelsea", "Manchester City FC": "Man City",
            "Man City": "Man City", "Manchester United FC": "Man United", "Man United": "Man United",
            "Tottenham Hotspur FC": "Tottenham", "Newcastle United FC": "Newcastle",
            "Aston Villa FC": "Aston Villa", "Liverpool FC": "Liverpool"
        }
        
        self.ratings = self.db.carregar_ratings()
        all_teams = pd.concat([self.df['HomeTeam'], self.df['AwayTeam']]).unique()
        for team in all_teams:
            if team not in self.ratings: self.ratings[team] = 1.0
                
        self._preparar_modelo_poisson()

    def _preparar_modelo_poisson(self):
        # Usar o histórico de 5 anos para ter médias mais robustas
        all_teams = pd.concat([self.df_h['HomeTeam'], self.df_h['AwayTeam']]).unique()
        self.team_stats = {}
        for team in all_teams:
            home_games = self.df_h[self.df_h['HomeTeam'] == team]
            away_games = self.df_h[self.df_h['AwayTeam'] == team]
            
            self.team_stats[team] = {
                'ataque_home': home_games['FTHG'].mean() if len(home_games) > 0 else 1.0,
                'defesa_home': home_games['FTAG'].mean() if len(home_games) > 0 else 1.2,
                'ataque_away': away_games['FTAG'].mean() if len(away_games) > 0 else 0.8,
                'defesa_away': away_games['FTHG'].mean() if len(away_games) > 0 else 1.5,
                'cs_home': (home_games['FTAG'] == 0).mean() if len(home_games) > 0 else 0.3,
                'cs_away': (home_games['FTHG'] == 0).mean() if len(away_games) > 0 else 0.2,
                'win_rate_home': (home_games['FTR'] == 'H').mean() if len(home_games) > 0 else 0.4,
                'win_rate_away': (away_games['FTR'] == 'A').mean() if len(away_games) > 0 else 0.2
            }
        self.media_gols_home = self.df_h['FTHG'].mean()
        self.media_gols_away = self.df_h['FTAG'].mean()

    def _get_team_stats(self, team):
        team = self.team_map.get(team, team)
        default = {'ataque_home': 1.0, 'defesa_home': 1.2, 'ataque_away': 0.8, 'defesa_away': 1.5, 'win_rate_home': 0.4, 'win_rate_away': 0.2}
        return self.team_stats.get(team, default)

    def get_h2h_stats(self, casa, fora):
        casa = self.team_map.get(casa, casa)
        fora = self.team_map.get(fora, fora)
        # Confrontos diretos nos últimos 5 anos
        h2h = self.df_h[((self.df_h['HomeTeam'] == casa) & (self.df_h['AwayTeam'] == fora)) | 
                       ((self.df_h['HomeTeam'] == fora) & (self.df_h['AwayTeam'] == casa))]
        h2h = h2h.sort_values('Date', ascending=False).head(5)
        
        if h2h.empty: return None
        
        wins_casa = len(h2h[(h2h['HomeTeam'] == casa) & (h2h['FTR'] == 'H')]) + len(h2h[(h2h['AwayTeam'] == casa) & (h2h['FTR'] == 'A')])
        avg_goals = (h2h['FTHG'] + h2h['FTAG']).mean()
        btts_perc = ((h2h['FTHG'] > 0) & (h2h['FTAG'] > 0)).mean()
        
        return {
            'total': len(h2h),
            'wins_casa': wins_casa,
            'avg_goals': avg_goals,
            'btts_perc': btts_perc,
            'last_results': h2h[['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']].to_dict('records')
        }

    def get_momentum(self, team):
        team = self.team_map.get(team, team)
        # Últimos 5 jogos no geral (independente de casa/fora)
        recent = self.df_h[(self.df_h['HomeTeam'] == team) | (self.df_h['AwayTeam'] == team)].sort_values('Date', ascending=False).head(5)
        if recent.empty: return None
        
        wins = 0
        gols_feitos = 0
        gols_sofridos = 0
        for _, r in recent.iterrows():
            if r['HomeTeam'] == team:
                gols_feitos += r['FTHG']; gols_sofridos += r['FTAG']
                if r['FTR'] == 'H': wins += 1
            else:
                gols_feitos += r['FTAG']; gols_sofridos += r['FTHG']
                if r['FTR'] == 'A': wins += 1
                
        return {
            'win_rate': wins / len(recent),
            'avg_gols_feitos': gols_feitos / len(recent),
            'avg_gols_sofridos': gols_sofridos / len(recent),
            'trend': "Subindo" if wins >= 3 else ("Descendo" if wins <= 1 else "Estável")
        }

    def calcular_probabilidade(self, casa, fora, fadiga_casa=False, fadiga_fora=False):
        casa = self.team_map.get(casa, casa)
        fora = self.team_map.get(fora, fora)
        
        rating_casa = self.ratings.get(casa, 1.0)
        rating_fora = self.ratings.get(fora, 1.0)
        
        if fadiga_casa: rating_casa *= 0.90
        if fadiga_fora: rating_fora *= 0.90
        
        stats_casa = self._get_team_stats(casa)
        stats_fora = self._get_team_stats(fora)
        
        lambda_home = (stats_casa['ataque_home'] * stats_fora['defesa_away']) / self.media_gols_home
        lambda_away = (stats_fora['ataque_away'] * stats_casa['defesa_home']) / self.media_gols_away
        
        prob_matrix = np.outer(poisson.pmf(range(7), lambda_home), poisson.pmf(range(7), lambda_away))
        
        p_home_poisson = np.sum(np.tril(prob_matrix, -1))
        p_draw = np.sum(np.diag(prob_matrix))
        p_away = np.sum(np.triu(prob_matrix, 1))
        
        # Média ponderada entre Rating e Poisson
        diff = (rating_casa - rating_fora) * 0.2
        prob_final = p_home_poisson + diff
        
        return min(0.95, max(0.05, prob_final))

    def gerar_recomendacoes(self, fixture, use_ai=False):
        casa, fora = fixture['Home'], fixture['Away']
        p_home = self.calcular_probabilidade(casa, fora)
        
        # Novos Dados para AI
        h2h = self.get_h2h_stats(casa, fora)
        mom_casa = self.get_momentum(casa)
        mom_fora = self.get_momentum(fora)
        
        ai_insight = None
        if use_ai:
            context = f"H2H: {h2h}. Momentum {casa}: {mom_casa}. Momentum {fora}: {mom_fora}."
            ai_insight = self.ai.analise_partida(casa, fora, context=context)
            adj = (ai_insight['sentimento'] * 0.1)
            p_home = min(0.99, max(0.01, p_home + adj))
        
        recoms = []
        if p_home > 0.68: recoms.append({'mercado': 'Vencedor: ' + casa, 'confianca': p_home, 'tipo': 'Principal'})
        elif p_home < 0.28: recoms.append({'mercado': 'Vencedor: ' + fora, 'confianca': 1-p_home, 'tipo': 'Principal'})
        
        # Over/Under e BTTS baseados no histórico filtrado
        p_over, p_btts = self.calcular_mercados_adicionais(casa, fora)
        if p_btts > 0.66: recoms.append({'mercado': 'Ambas Marcam: Sim', 'confianca': p_btts, 'tipo': 'Golos'})
        if p_over > 0.68: recoms.append({'mercado': 'Over 2.5 Gols', 'confianca': p_over, 'tipo': 'Golos'})
        
        return recoms, ai_insight

    def calcular_mercados_adicionais(self, casa, fora, fadiga_casa=False, fadiga_fora=False):
        stats_casa = self._get_team_stats(casa)
        stats_fora = self._get_team_stats(fora)
        lambda_home = (stats_casa['ataque_home'] * stats_fora['defesa_away']) / self.media_gols_home
        lambda_away = (stats_fora['ataque_away'] * stats_casa['defesa_home']) / self.media_gols_away
        if fadiga_casa: lambda_home *= 0.9
        if fadiga_fora: lambda_away *= 0.9
        prob_matrix = np.outer(poisson.pmf(range(7), lambda_home), poisson.pmf(range(7), lambda_away))
        p_over25 = 1 - np.sum(np.array([prob_matrix[i,j] for i in range(7) for j in range(7) if i+j <= 2]))
        p_btts = sum(prob_matrix[i, j] for i in range(1, 7) for j in range(1, 7))
        return p_over25, p_btts
    
    def get_ev(self, prob_ia, odd_mercado):
        if odd_mercado <= 0: return 0
        return (prob_ia * odd_mercado) - 1

    def calcular_kelly(self, prob, odd, banca, risco_max):
        if odd <= 1: return 0, 0
        q = 1 - prob
        kelly = (prob * (odd - 1) - q) / (odd - 1)
        kelly_frat = max(0, kelly * 0.5)
        kelly_safe = min(kelly_frat, risco_max / 100)
        return kelly_safe * banca, kelly_safe

    def atualizar_ratings_resultado(self, casa, fora, p_ia, res_real, k=0.1):
        erro = res_real - p_ia
        self.ratings[casa] += k * erro
        self.ratings[fora] -= k * erro
        return erro ** 2
