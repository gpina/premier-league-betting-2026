import requests
import json
import random
import streamlit as st

class AIService:
    def __init__(self):
        # Chaves agora vêm de st.secrets (Segurança GitHub)
        try:
            self.gemini_keys = st.secrets["gemini"]["keys"]
            self.groq_key = st.secrets["groq"]["api_key"]
            self.openrouter_key = st.secrets["openrouter"]["api_key"]
        except Exception:
            self.gemini_keys = []
            self.groq_key = ""
            self.openrouter_key = ""
        
    def _get_gemini_analysis(self, prompt, key):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
            }
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        return None

    def _get_groq_analysis(self, prompt):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return None

    def _get_external_insights(self, casa, fora):
        try:
            with open("external_insights.json", "r") as f:
                data = json.load(f)
            fixture = f"{casa} vs {fora}"
            # Busca em datas ou no Geral
            insights = []
            for date, matches in data.items():
                if fixture in matches: insights.append(matches[fixture])
            if fixture in data.get("General", {}):
                insights.append(data["General"][fixture])
            return " | ".join(insights) if insights else "Nenhuma opinião externa recente encontrada."
        except: return ""

    def analise_partida(self, casa, fora, context=""):
        if not self.gemini_keys and not self.groq_key:
            return {"sentimento": 0.0, "justificativa": "Aguardando configuração de API Secrets.", "pontos_chave": ["N/A"], "vencedor_provavel": "N/A"}

        external = self._get_external_insights(casa, fora)
        
        prompt = f"""
        Você é um analista especialista em apostas da Premier League.
        Analise o confronto: {casa} vs {fora}.
        Contexto Estatístico (H2H/Forma): {context}
        Opiniões Externas (Experts): {external}
        
        Retorne APENAS um JSON:
        {{
            "sentimento": valor_entre_-1_e_1,
            "justificativa": "string resumindo os dados + opiniões de experts",
            "pontos_chave": ["ponto 1", "ponto 2"],
            "vencedor_provavel": "string"
        }}
        """
        
        # Rotação Gemini
        keys_random = self.gemini_keys.copy()
        random.shuffle(keys_random)
        for key in keys_random:
            try:
                raw = self._get_gemini_analysis(prompt, key)
                if raw: return json.loads(raw)
            except: continue
                
        # Fallback Groq
        try:
            raw = self._get_groq_analysis(prompt)
            if raw: return json.loads(raw)
        except: pass
            
        return {"sentimento": 0.0, "justificativa": "Análise IA indisponível.", "pontos_chave": ["N/A"], "vencedor_provavel": "Empate"}
