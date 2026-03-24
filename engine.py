import pandas as pd
import numpy as np
from scipy.stats import poisson
import streamlit as st
from ai_service import AIService

class EngineAprendizagem:
    def __init__(self, data_path='E0.csv'):
        self.df = pd.read_csv(data_path)
        self.df['Date'] = pd.to_datetime(self.df['Date'], dayfirst=True)
        self.ai = AIService()
        self._preparar_modelo()

    def _preparar_modelo(self):
        # Cálculos de força (Poisson)
        all_teams = pd.concat([self.df['HomeTeam'], self.df['AwayTeam']]).unique()
        self.team_stats = {}
        for team in all_teams:
            home_games = self.df[self.df['HomeTeam'] == team]
            away_games = self.df[self.df['AwayTeam'] == team]
            self.team_stats[team] = {
                'ataque_home': home_games['FTHG'].mean(),
                'defesa_home': home_games['FTAG'].mean(),
                'ataque_away': away_games['FTAG'].mean(),
                'defesa_away': away_games['FTHG'].mean()
            }
        self.media_gols_home = self.df['FTHG'].mean()
        self.media_gols_away = self.df['FTAG'].mean()

    def prever_partida(self, home, away):
        if home not in self.team_stats or away not in self.team_stats:
            return None
        
        lambda_home = (self.team_stats[home]['ataque_home'] * self.team_stats[away]['defesa_away']) / self.media_gols_home
        lambda_away = (self.team_stats[away]['ataque_away'] * self.team_stats[home]['defesa_home']) / self.media_gols_away
        
        # Probabilidades de placar (até 6 gols)
        prob_matrix = np.outer(poisson.pmf(range(7), lambda_home), poisson.pmf(range(7), lambda_away))
        
        p_home = np.sum(np.triu(prob_matrix, 1).T)
        p_draw = np.sum(np.diag(prob_matrix))
        p_away = np.sum(np.tril(prob_matrix, -1).T)
        
        # Mercados Adicionais
        prob_btts = sum(prob_matrix[i, j] for i in range(1, 7) for j in range(1, 7))
        prob_over15 = 1 - (prob_matrix[0,0] + prob_matrix[0,1] + prob_matrix[1,0])
        prob_over25 = 1 - np.sum(np.array([prob_matrix[i,j] for i in range(7) for j in range(7) if i+j <= 2]))
        prob_over35 = 1 - np.sum(np.array([prob_matrix[i,j] for i in range(7) for j in range(7) if i+j <= 3]))
        
        return {
            '1': p_home, 'X': p_draw, '2': p_away,
            'BTTS': prob_btts, 'Over1.5': prob_over15, 'Over2.5': prob_over25, 'Over3.5': prob_over35,
            '1X': p_home + p_draw, 'X2': p_draw + p_away, '12': p_home + p_away
        }

    def gerar_recomendacoes(self, fixture, use_ai=False):
        casa, fora = fixture['Home'], fixture['Away']
        probs = self.prever_partida(casa, fora)
        if not probs: return []
        
        # Se usar IA, buscar sentimento tático
        ai_insight = None
        if use_ai:
            ai_insight = self.ai.analise_partida(casa, fora)
            # O sentimento IA (-1 a 1) ajusta a confiança base
            adj = (ai_insight['sentimento'] * 0.1) # Ajuste de até 10%
            probs['1'] = min(0.99, max(0.01, probs['1'] + adj))
            probs['2'] = min(0.99, max(0.01, probs['2'] - adj))
        
        recoms = []
        # Lógica de Valor (Simplificada: Se prob > 60%, recomendar)
        if probs['1'] > 0.65: recoms.append({'mercado': 'Vencedor: ' + casa, 'confianca': probs['1'], 'tipo': 'Principal'})
        if probs['2'] > 0.65: recoms.append({'mercado': 'Vencedor: ' + fora, 'confianca': probs['2'], 'tipo': 'Principal'})
        if probs['BTTS'] > 0.68: recoms.append({'mercado': 'Ambas Marcam: Sim', 'confianca': probs['BTTS'], 'tipo': 'Golos'})
        if probs['Over2.5'] > 0.65: recoms.append({'mercado': 'Over 2.5 Gols', 'confianca': probs['Over2.5'], 'tipo': 'Golos'})
        if probs['1X'] > 0.85: recoms.append({'mercado': 'Chance Dupla: ' + casa + ' ou Empate', 'confianca': probs['1X'], 'tipo': 'Segurança'})
        
        return recoms, ai_insight
