import numpy as np

class EngineAprendizagem:
    """
    O 'Cérebro' do sistema: Cálculos de probabilidade, Brier Score e ajuste de ratings.
    """
    def __init__(self, ratings_iniciais=None):
        # Ratings base (1.0 = Médio/Neutro)
        self.ratings = ratings_iniciais if ratings_iniciais else {
            "Man City": 1.45,
            "Arsenal": 1.40,
            "Liverpool": 1.35,
            "Chelsea": 1.20,
            "Everton": 0.95,
            "Brentford": 1.05,
            "Tottenham": 1.25,
            "Man United": 1.15,
            "Newcastle": 1.10,
            "Aston Villa": 1.25
        }
        self.fator_aprendizagem = 0.05

    def calcular_probabilidade(self, casa, fora, fadiga_casa=False, fadiga_fora=False):
        """Calcula a probabilidade de vitória da casa baseada nos ratings e fadiga."""
        r_casa = self.ratings.get(casa, 1.0)
        r_fora = self.ratings.get(fora, 1.0)
        
        # Penalização por fadiga (Ex: Reduz 10% da força se jogou no meio da semana)
        if fadiga_casa: r_casa *= 0.90
        if fadiga_fora: r_fora *= 0.90
        
        return r_casa / (r_casa + r_fora)

    def calcular_kelly(self, prob_ia, odd_mercado, banca_total, risco_max_percentual=2):
        """
        Calcula o valor sugerido de aposta usando Kelly Fracionário (50%)
        """
        if odd_mercado <= 1: return 0.0, 0.0
        
        b = odd_mercado - 1
        p = prob_ia
        q = 1 - p
        
        # Fórmula de Kelly bruto
        f_kelly = (b * p - q) / b
        
        # Kelly Fracionário (50% de segurança)
        f_kelly_ajustado = f_kelly * 0.5
        
        # Limitar pelo risco máximo definido pelo utilizador
        percentual_final = min(max(0, f_kelly_ajustado), risco_max_percentual / 100)
        
        valor_aposta = percentual_final * banca_total
        return valor_aposta, f_kelly

    def atualizar_ratings_resultado(self, casa, fora, prev_casa, resultado_final):
        """
        Ajusta os ratings baseados no erro (Brier Score).
        resultado_final: 1 (Vitória Casa), 0.5 (Empate), 0 (Vitória Fora)
        """
        # Garantir que as equipas existem no dicionário para evitar KeyError
        if casa not in self.ratings: self.ratings[casa] = 1.0
        if fora not in self.ratings: self.ratings[fora] = 1.0

        # Erro Brier: (Probabilidade - Resultado Real)^2
        erro = (prev_casa - resultado_final) ** 2
        
        # Se a IA subestimou o vencedor (prev < 0.5 e ganhou)
        if resultado_final == 1 and prev_casa < 0.5:
            self.ratings[casa] += self.fator_aprendizagem
            self.ratings[fora] -= self.fator_aprendizagem / 2
        
        # Se a IA superestimou (prev > 0.7 e não ganhou)
        elif resultado_final != 1 and prev_casa > 0.7:
            self.ratings[casa] -= self.fator_aprendizagem
            self.ratings[fora] += self.fator_aprendizagem / 2
            
        return erro

    def get_ev(self, prob_ia, odd_mercado):
        """Valor Esperado (Expected Value)"""
        return (prob_ia * odd_mercado) - 1
