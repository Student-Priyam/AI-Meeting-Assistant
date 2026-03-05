# --- 1. PYTHON 3.13 COMPATIBILITY SHIM ---
try:
    import audioop
except ImportError:
    import audioop_lts as audioop
    import sys
    sys.modules['audioop'] = audioop

import streamlit as st
import whisper
import requests 
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import re
import os
import sqlite3
import tempfile
from datetime import datetime
from pydub import AudioSegment  

# --- 2. CORE DATABASE SYSTEM ---
def init_db():
    conn = sqlite3.connect('strategic_intel_v8.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, type TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 2.1 STABLE HUGGING FACE LOGIC ---
def ask_ai_assistant(transcript, user_query):
    if "HF_TOKEN" not in st.secrets:
        return "Error: HF_TOKEN missing in Streamlit Secrets."
    
    # Stable Mistral model via Hugging Face Inference API
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
    headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}
    
    # Clean logic to ensure AI only answers based on meeting
    prompt = f"<s>[INST] Use the following transcript to answer the question briefly.\nTranscript: {transcript}\nQuestion: {user_query} [/INST]</s>"
    
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150, "return_full_text": False}}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            result = response.json()
            return result[0]['generated_text'].strip()
        else:
            return f"AI is warming up (Error {response.status_code}). Try again in 5 seconds."
    except:
        return "Connection busy. Please retry."

# --- 3. PREMIUM UI/UX CONFIG ---
st.set_page_config(page_title="Strategic Intel | AI Assistant", layout="wide", page_icon="💼")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .hero-banner {
        background: linear-gradient(135deg, #005A92 0%, #00426d 100%);
        padding: 3rem 2rem; border-radius: 16px; margin-bottom: 2.5rem;
        color: white; text-align: center;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
    }
    .hero-banner h1 { font-size: 2.8rem; font-weight: 700; color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>STRATEGIC MINUTES</h2>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Technical Sync"])
    choice = st.radio("Navigation", ["🚀 Meeting Summary", "📅 Meeting Archives"], label_visibility="collapsed")

# --- TAB 1: SUMMARY & CHAT ---
if choice == "🚀 Meeting Summary":
    st.markdown(f"""
    <div class="hero-banner">
        <div style="margin-bottom: 1.5rem;">
            <img src="https://images.unsplash.com/photo-1616531770192-6eaea74c2456?auto=format&fit=crop&q=60&w=1200" 
                 style="border-radius:12px; max-width:600px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);"/>
        </div>
        <h1>Intelligence Mode: {m_type}</h1>
        <p>Your session analysis will appear below after processing.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="executive-card" style="background:white; padding:20px; border-radius:12px;">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"])
    title = st.text_input("Session Title")
    
    if file and st.button("Generate Intelligence Report", type="primary", use_container_width=True):
        with st.spinner("Decoding Meeting..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                
                # Whisper Logic (using existing function)
                model = whisper.load_model("base")
                result = model.transcribe(tmp.name)
                raw_text = result["text"]

            # BART Summarizer
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:3000], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            st.session_state.update({'summary': summary, 'current_transcript': raw_text})
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if 'summary' in st.session_state:
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📝 Executive Summary")
            st.info(st.session_state['summary'])

        with c2:
            st.markdown("#### 🤖 AI Chat Assistant")
            if "messages" not in st.session_state: st.session_state.messages = []
            
            chat_container = st.container(height=350)
            with chat_container:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])

            if p := st.chat_input("Ask about the meeting..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with chat_container:
                    with st.chat_message("user"): st.markdown(p)
                    with st.chat_message("assistant"):
                        ans = ask_ai_assistant(st.session_state['current_transcript'], p)
                        st.markdown(ans)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
