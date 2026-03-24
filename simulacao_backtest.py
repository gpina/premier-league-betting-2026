import pandas as pd
from engine import EngineAprendizagem

def executar_backtest(rodadas=3, use_ai=False):
    engine = EngineAprendizagem()
    # Pegar os últimos jogos do CSV (simulando rodadas recentes)
    df_recent = engine.df.tail(rodadas * 10) # Aproximadamente 10 jogos por rodada
    
    resultados = []
    acertos = 0
    total = 0
    
    for _, match in df_recent.iterrows():
        fixture = {'Home': match['HomeTeam'], 'Away': match['AwayTeam']}
        recoms, ai_info = engine.gerar_recomendacoes(fixture, use_ai=use_ai)
        
        res_real = "1" if match['FTHG'] > match['FTAG'] else ("2" if match['FTAG'] > match['FTHG'] else "X")
        btts_real = match['FTHG'] > 0 and match['FTAG'] > 0
        over25_real = (match['FTHG'] + match['FTAG']) > 2.5
        
        for rec in recoms:
            ganhou = False
            if "Vencedor" in rec['mercado']:
                time_rec = rec['mercado'].split(": ")[1]
                if (time_rec == match['HomeTeam'] and res_real == "1") or \
                   (time_rec == match['AwayTeam'] and res_real == "2"):
                    ganhou = True
            elif "Ambas Marcam" in rec['mercado'] and btts_real: ganhou = True
            elif "Over 2.5" in rec['mercado'] and over25_real: ganhou = True
            elif "1X" in rec['mercado'] and (res_real == "1" or res_real == "X"): ganhou = True
            
            resultados.append({
                'Jogo': f"{match['HomeTeam']} vs {match['AwayTeam']}",
                'Aposta': rec['mercado'],
                'Confiança': f"{rec['confianca']:.1%}",
                'Resultado': "✅ GREEN" if ganhou else "❌ RED",
                'Ganhos': 1.0 if ganhou else -1.0
            })
            if ganhou: acertos += 1
            total += 1
            
    return pd.DataFrame(resultados), (acertos/total if total > 0 else 0)

if __name__ == "__main__":
    df, win_rate = executar_backtest()
    print(f"Win Rate: {win_rate:.1%}")
    print(df.head())
