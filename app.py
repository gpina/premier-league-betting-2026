import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import os
from engine import EngineAprendizagem
from database import Database
from api_client import FootballDataClient
from datetime import datetime

# Configurações Globais
st.set_page_config(page_title="Premier League Strategic Dashboard 2026", layout="wide", page_icon="⚽")
db = Database()
api_free = FootballDataClient() 

# Carregar Dados Qualitativos
def carregar_contexto():
    caminho = "qualitative_context.json"
    if os.path.exists(caminho):
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_contexto(novo_contexto):
    caminho = "qualitative_context.json"
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(novo_contexto, f, indent=4, ensure_ascii=False)

contexto = carregar_contexto()
last_upd = contexto.get('last_update', 'N/A')

# Inicialização do Motor
ratings_carregados = db.carregar_ratings()
engine = EngineAprendizagem(ratings_iniciais=ratings_carregados)

# Estilo Personalizado (CSS)
st.markdown("""
<style>
    .main { background-color: #f5f7f9; font-family: 'Inter', sans-serif; }
    .stMetric { background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .injury-card { background-color: #fff4f4; border-left: 5px solid #ff4b4b; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
    .suspension-card { background-color: #fff9e6; border-left: 5px solid #ffa500; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
    .fatigue-card { background-color: #f0f7ff; border-left: 5px solid #007bff; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("💰 Gestão de Banca")
banca_total = st.sidebar.number_input("Banca Total (€)", value=1000.0, step=10.0)
risco_max = st.sidebar.slider("Risco Máximo por Aposta (%)", 1, 5, 2)

# --- CABEÇALHO ---
st.title("🏆 Premier League: Caderno Estratégico AI")
st.markdown(f"**Modo:** Analista Tático Progressivo | **Status:** Online | **Contexto:** {last_upd}")

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Prognósticos & Fadiga", "🧠 Aprendizagem (CSV)", "📜 Histórico", "🔧 Admin Contexto"])

with tab1:
    st.subheader("⚽ Previsão de Próximos Confrontos")
    col_input, col_context = st.columns([2, 1.5])
    
    with col_input:
        proximos = api_free.get_mock_next_fixtures()
        idx_p = st.selectbox("Selecionar Jogo do Calendário", range(len(proximos)), 
                             format_func=lambda i: f"{proximos[i]['casa']} vs {proximos[i]['fora']} ({proximos[i]['data']})")
        
        jogo_sel = proximos[idx_p]
        time_casa, time_fora = jogo_sel['casa'], jogo_sel['fora']
        
        # Ajustes Táticos (Fadiga Europeia)
        st.write("**Factores Táticos de Fadiga**")
        c1, c2 = st.columns(2)
        fadiga_casa = c1.checkbox(f"Fadiga Europeia ({time_casa})", help="Assinalar se a equipa teve jogo da Champions/Europa League a meio da semana.")
        fadiga_fora = c2.checkbox(f"Fadiga Europeia ({time_fora})")
        
        odd_mercado = st.number_input("Odd da Casa", value=float(jogo_sel['odd']), step=0.01)
        
        # Cálculos de IA com Fadiga
        prob_ia = engine.calcular_probabilidade(time_casa, time_fora, fadiga_casa, fadiga_fora)
        ev = engine.get_ev(prob_ia, odd_mercado)
        valor_aposta, kelly_puro = engine.calcular_kelly(prob_ia, odd_mercado, banca_total, risco_max)

        m1, m2, m3 = st.columns(3)
        m1.metric("Probabilidade IA", f"{prob_ia:.1%}")
        m2.metric("Expected Value", f"{ev:.2%}", delta=f"{ev:.2%}" if ev > 0 else f"{ev:.2%}")
        m3.metric("Sugestão Aposta", f"{valor_aposta:.2f}€")

        if ev > 0.05:
            st.success(f"📈 **OPORTUNIDADE:** Valor detectado!")
        else:
            st.info("⚖️ **MERCADO AJUSTADO**")
        
        if st.button("💾 Gravar esta Previsão", help="Guarda a previsão para validação futura após o jogo."):
            db.salvar_previsao_pendente(jogo_sel['data'], time_casa, time_fora, prob_ia, odd_mercado, ev, valor_aposta)
            st.toast("Previsão guardada com sucesso!")

    st.markdown("---")
    st.subheader("📈 Mercados Adicionais (Golos)")
    col_goal1, col_goal2 = st.columns(2)
    
    p_over, p_btts = engine.calcular_mercados_adicionais(time_casa, time_fora, fadiga_casa, fadiga_fora)
    
    with col_goal1:
        st.write("**Over 2.5 Golos**")
        odd_over = st.number_input("Odd Over 2.5", value=1.90, step=0.01)
        ev_over = engine.get_ev(p_over, odd_over)
        st.metric("Probabilidade Over 2.5", f"{p_over:.1%}", delta=f"{ev_over:.2%}")
        if ev_over > 0.05: st.success("🔥 Valor p/ Over 2.5!")

    with col_goal2:
        st.write("**Ambas Marcam (BTTS)**")
        odd_btts = st.number_input("Odd BTTS Sim", value=1.80, step=0.01)
        ev_btts = engine.get_ev(p_btts, odd_btts)
        st.metric("Probabilidade BTTS", f"{p_btts:.1%}", delta=f"{ev_btts:.2%}")
        if ev_btts > 0.05: st.success("⚽ Valor p/ Ambas Marcam!")

    with col_context:
        st.write("📋 **Relatório Tático (NotebookLM)**")
        if fadiga_casa or fadiga_fora:
            st.markdown("<div class='fatigue-card'>⚠️ <b>ALERTA DE FADIGA:</b> Uma das equipas em campo teve desgaste europeu. O modelo aplicou uma penalização de 10% na força ofensiva.</div>", unsafe_allow_html=True)
        
        for time in [time_casa, time_fora]:
            st.markdown(f"**{time}**")
            info = contexto.get(time, {})
            if info.get('lesionados'):
                st.markdown(f"<div class='injury-card'><b>Lesionados:</b> {', '.join(info['lesionados'])}</div>", unsafe_allow_html=True)
            if info.get('suspensos'):
                st.markdown(f"<div class='suspension-card'><b>Suspensos:</b> {', '.join(info['suspensos'])}</div>", unsafe_allow_html=True)
            if not info.get('lesionados') and not info.get('suspensos'):
                st.write("✅ Sem baixas críticas.")

with tab2:
    st.subheader("🧠 Motor de Aprendizagem (CSV)")
    col_raw, col_learn = st.columns([1, 1])
    
    with col_raw:
        st.write("**Histórico de Resultados (CSV)**")
        df_recent = api_free.carregar_resultados_recentes()
        if not df_recent.empty:
            st.dataframe(df_recent.head(10), use_container_width=True)
        else:
            st.error("Erro ao carregar CSV")

    with col_learn:
        st.write("📈 **Treinar IA**")
        if not df_recent.empty:
            # Opção 1: Aprender com o último jogo (Individual)
            ultimo = df_recent.iloc[0]
            st.info(f"Último Jogo: **{ultimo['casa']} {ultimo['golos_casa']} - {ultimo['golos_fora']} {ultimo['fora']}**")
            
            with st.container():
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Aprender com este Resultado"):
                        res_val = 1.0 if ultimo['golos_casa'] > ultimo['golos_fora'] else (0.5 if ultimo['golos_casa'] == ultimo['golos_fora'] else 0.0)
                        p_ia = engine.calcular_probabilidade(ultimo['casa'], ultimo['fora'])
                        erro = engine.atualizar_ratings_resultado(ultimo['casa'], ultimo['fora'], p_ia, res_val)
                        db.salvar_ratings(engine.ratings)
                        db.registrar_partida(str(ultimo['data']), f"{ultimo['casa']} vs {ultimo['fora']}", ultimo['casa'], ultimo['fora'], float(ultimo['odd_casa']), p_ia, res_val, erro, 0)
                        st.success("IA Evoluída!")
                        st.rerun()

                with c2:
                    if st.button("🚀 Processar Todos (Batch)", help="Processa todos os resultados do CSV para atualizar os ratings de uma só vez."):
                        count = 0
                        # Inverter para processar do mais antigo para o mais recente para a aprendizagem ser sequencial correta
                        for _, row in df_recent.iloc[::-1].iterrows():
                            # Só processar se o jogo ainda não estiver no histórico para evitar duplicação (simplificado por enquanto)
                            res_val = 1.0 if row['golos_casa'] > row['golos_fora'] else (0.5 if row['golos_casa'] == row['golos_fora'] else 0.0)
                            p_ia = engine.calcular_probabilidade(row['casa'], row['fora'])
                            erro = engine.atualizar_ratings_resultado(row['casa'], row['fora'], p_ia, res_val)
                            db.registrar_partida(str(row['data']), f"{row['casa']} vs {row['fora']}", row['casa'], row['fora'], float(row['odd_casa']), p_ia, res_val, erro, 0)
                            count += 1
                        
                        db.salvar_ratings(engine.ratings)
                        st.success(f"IA Treinada com {count} jogos!")
                        st.rerun()

with tab3:
    st.subheader("📜 Evolução da Capacidade Preditiva")
    df_ratings = db.get_df_ratings()
    st.write("**Ranking de Força Dinâmico**")
    st.dataframe(df_ratings, use_container_width=True)
    
    historico = db.get_df_historico()
    if not historico.empty:
        st.write("**Gráfico de Melhoria (Erro Brier)**")
        # Quanto mais baixo o erro, melhor a IA
        st.line_chart(historico['erro_brier'])
        st.write("**Resultados Validados**")
        st.dataframe(historico, use_container_width=True)
    
    previsoes = db.get_previsoes_pendentes()
    if not previsoes.empty:
        st.write("**🔮 Previsões a Aguardar Resultado**")
        st.dataframe(previsoes, use_container_width=True)

with tab4:
    st.subheader("🔧 Gestão de Contexto Tático (Admin)")
    
    # Proteção por Senha (Definir em Settings -> Secrets no Streamlit Cloud)
    # Se não houver segredo definido, o padrão é 'admin123'
    senha_correta = st.secrets.get("admin_password", "admin123")
    
    col_lock, col_auth = st.columns([1, 3])
    with col_lock:
        st.write("🔐 **Acesso Restrito**")
    with col_auth:
        senha_inserida = st.text_input("Introduza a senha para editar", type="password")

    if senha_inserida == senha_correta:
        st.success("Autenticado! Pode atualizar o contexto qualitativo.")
        
        time_edit = st.selectbox("Selecionar Equipa", sorted(engine.ratings.keys()))
        
        col_ed1, col_ed2 = st.columns(2)
        current_info = contexto.get(time_edit, {})
        
        les_str = col_ed1.text_area("Lesionados (um por linha)", value="\n".join(current_info.get('lesionados', [])))
        sus_str = col_ed2.text_area("Suspensos (um por linha)", value="\n".join(current_info.get('suspensos', [])))
        
        if st.button("💾 Gravar Alterações para " + time_edit):
            contexto[time_edit] = {
                "lesionados": [x.strip() for x in les_str.split("\n") if x.strip()],
                "suspensos": [x.strip() for x in sus_str.split("\n") if x.strip()]
            }
            contexto['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            salvar_contexto(contexto)
            st.toast(f"Dados de {time_edit} atualizados com sucesso!")
            st.rerun()
    elif senha_inserida:
        st.error("Senha incorreta. Acesso negado.")
