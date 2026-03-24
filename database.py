import sqlite3
import pandas as pd
import json

class Database:
    """
    Base de dados SQLite para armazenar o histórico de xG, Odds e o estado dos Ratings.
    """
    def __init__(self, db_path="premier_stats.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de Ratings (Atual)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ratings (
                    equipa TEXT PRIMARY KEY,
                    rating REAL,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de Histórico de Jogos e Erros
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico_jogos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    jogo TEXT,
                    casa TEXT,
                    fora TEXT,
                    odd_mercado REAL,
                    prob_ia REAL,
                    resultado_real INTEGER,
                    erro_brier REAL,
                    ev REAL
                )
            """)
            
            # Tabela de Previsões Pendentes (Prognósticos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS previsoes_pendentes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    casa TEXT,
                    fora TEXT,
                    prob_ia REAL,
                    odd_mercado REAL,
                    ev REAL,
                    valor_sugerido REAL
                )
            """)
            conn.commit()

    def salvar_ratings(self, ratings_dict):
        with sqlite3.connect(self.db_path) as conn:
            for equipa, rating in ratings_dict.items():
                conn.execute(
                    "INSERT OR REPLACE INTO ratings (equipa, rating) VALUES (?, ?)",
                    (equipa, rating)
                )
            conn.commit()

    def carregar_ratings(self):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql("SELECT equipa, rating FROM ratings", conn)
            if df.empty:
                return None
            return dict(zip(df['equipa'], df['rating']))

    def registrar_partida(self, data, jogo, casa, fora, odd, prob, resultado, erro, ev):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO historico_jogos (data, jogo, casa, fora, odd_mercado, prob_ia, resultado_real, erro_brier, ev)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data, jogo, casa, fora, odd, prob, resultado, erro, ev))
            conn.commit()

    def salvar_previsao_pendente(self, data, casa, fora, prob, odd, ev, valor):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO previsoes_pendentes (data, casa, fora, prob_ia, odd_mercado, ev, valor_sugerido)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data, casa, fora, prob, odd, ev, valor))
            conn.commit()

    def get_previsoes_pendentes(self):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql("SELECT * FROM previsoes_pendentes", conn)

    def get_df_ratings(self):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql("SELECT * FROM ratings ORDER BY rating DESC", conn)

    def get_df_historico(self):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql("SELECT * FROM historico_jogos ORDER BY id DESC", conn)
