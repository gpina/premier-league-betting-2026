import numpy as np
import math

class EngineAprendizagem:
    """
    O 'Cérebro' do sistema: Cálculos de probabilidade, Brier Score e ajuste de ratings.
    """
    def __init__(self, ratings_iniciais=None):
        # Ratings base (1.0 = Médio/Neutro)
        self.ratings = ratings_iniciais if ratings_iniciais else {
            "Man City": 1.45, "Arsenal": 1.40, "Liverpool": 1.35, "Chelsea": 1.20,
            "Everton": 0.95, "Brentford": 1.05, "Tottenham": 1.25, "Man United": 1.15,
            "Newcastle": 1.10, "Aston Villa": 1.25
        }
        self.fator_aprendizagem = 0.05
        self.media_golos_liga = 2.8 # Média base da Premier League

    def calcular_probabilidade(self, casa, fora, fadiga_casa=False, fadiga_fora=False):
        """Calcula a probabilidade de vitória da casa baseada nos ratings e fadiga."""
        r_casa = self.ratings.get(casa, 1.0)
        r_fora = self.ratings.get(fora, 1.0)
        if fadiga_casa: r_casa *= 0.90
        if fadiga_fora: r_fora *= 0.90
        return r_casa / (r_casa + r_fora)

    def estimar_xG(self, casa, fora, fadiga_casa=False, fadiga_fora=False):
        """Estima os golos esperados (xG) para cada equipa."""
        r_casa = self.ratings.get(casa, 1.0)
        r_fora = self.ratings.get(fora, 1.0)
        
        # Fator Casa (Geralmente 1.2x mais golos em casa na PL)
        base_casa = (self.media_golos_liga / 2) * 1.1
        base_fora = (self.media_golos_liga / 2) * 0.9

        xg_casa = base_casa * (r_casa / r_fora)
        xg_fora = base_fora * (r_fora / r_casa)
        
        if fadiga_casa: xg_casa *= 0.85
        if fadiga_fora: xg_fora *= 0.85
        
        return xg_casa, xg_fora

    def poisson_prob(self, k, lamb):
        """Cálculo manual de Poisson: (lambda^k * e^-lambda) / k!"""
        return (lamb**k * math.exp(-lamb)) / math.factorial(k)

    def calcular_mercados_adicionais(self, casa, fora, fadiga_casa=False, fadiga_fora=False):
        """Calcula Over 2.5 e BTTS usando distribuição de Poisson."""
        xg_c, xg_f = self.estimar_xG(casa, fora, fadiga_casa, fadiga_fora)
        
        # Probabilidade de cada score até 5 golos
        p_casa = [self.poisson_prob(i, xg_c) for i in range(6)]
        p_fora = [self.poisson_prob(j, xg_f) for j in range(6)]
        
        # BTTS: 1 - (Prob Casa 0 * Prob Fora 0)
        prob_btts = 1 - (self.poisson_prob(0, xg_c) * self.poisson_prob(0, xg_f))
        
        # Over 2.5: 1 - Sum(Scores com total <= 2)
        # Scores <= 2: (0,0), (1,0), (0,1), (2,0), (0,2), (1,1)
        prob_under_25 = 0
        for i in range(3):
            for j in range(3 - i):
                prob_under_25 += self.poisson_prob(i, xg_c) * self.poisson_prob(j, xg_f)
        
        prob_over_25 = 1 - prob_under_25
        return prob_over_25, prob_btts

    def calcular_kelly(self, prob_ia, odd_mercado, banca_total, risco_max_percentual=2):
        if odd_mercado <= 1: return 0.0, 0.0
        b = odd_mercado - 1
        p = prob_ia
        q = 1 - p
        f_kelly = (b * p - q) / b
        f_kelly_ajustado = f_kelly * 0.5
        percentual_final = min(max(0, f_kelly_ajustado), risco_max_percentual / 100)
        valor_aposta = percentual_final * banca_total
        return valor_aposta, f_kelly

    def atualizar_ratings_resultado(self, casa, fora, prev_casa, resultado_final):
        if casa not in self.ratings: self.ratings[casa] = 1.0
        if fora not in self.ratings: self.ratings[fora] = 1.0
        erro = (prev_casa - resultado_final) ** 2
        if resultado_final == 1 and prev_casa < 0.5:
            self.ratings[casa] += self.fator_aprendizagem
            self.ratings[fora] -= self.fator_aprendizagem / 2
        elif resultado_final != 1 and prev_casa > 0.7:
            self.ratings[casa] -= self.fator_aprendizagem
            self.ratings[fora] += self.fator_aprendizagem / 2
        return erro

    def get_ev(self, prob_ia, odd_mercado):
        return (prob_ia * odd_mercado) - 1
