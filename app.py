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

def delete_record(record_id):
    conn = sqlite3.connect('strategic_intel_v8.db')
    conn.execute("DELETE FROM archives WHERE id=?", (record_id,))
    conn.commit()
    conn.close()

init_db()

# --- 2.1 STABLE AI LOGIC (FIXED FOR 410 ERROR) ---
def ask_ai_assistant(transcript, user_query):
    if "HF_TOKEN" not in st.secrets:
        return "Error: HF_TOKEN missing in Streamlit Secrets."
    
    api_key = st.secrets["HF_TOKEN"]
    # UPDATED: Using the latest stable router URL and Mistral v0.3
    API_URL = "https://router.huggingface.co/hf-inference/models/mistralai/Mistral-7B-Instruct-v0.3"
    
    headers = {"Authorization": f"Bearer {api_key}"}
    prompt = f"<s>[INST] Context: {transcript}\n\nQuestion: {user_query}\n\nAnswer briefly: [/INST]</s>"
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150, "return_full_text": False}}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            result = response.json()
            return result[0]['generated_text'].strip()
        else:
            return f"AI Error {response.status_code}: Please check your HF_TOKEN permissions in Settings."
    except Exception as e:
        return f"Connection failed: {str(e)}"

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
    .executive-card {
        background: white; padding: 2.5rem; border-radius: 12px; border: 1px solid #E2E8F0; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1.5rem; 
    }
</style>
""", unsafe_allow_html=True)

# --- 4. AUDIO PROCESSING (WHISPER) ---
def transcribe_long_audio(file_path):
    model = whisper.load_model("base")
    audio = AudioSegment.from_file(file_path)
    chunk_length = 5 * 60 * 1000 
    chunks = [audio[i:i + chunk_length] for i in range(0, len(audio), chunk_length)]
    full_transcript = ""
    p_bar = st.progress(0)
    for i, chunk in enumerate(chunks):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            chunk.export(tmp.name, format="wav")
            result = model.transcribe(tmp.name)
            full_transcript += result["text"] + " "
            os.remove(tmp.name)
        p_bar.progress((i + 1) / len(chunks))
    return full_transcript

# --- 5. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>STRATEGIC MINUTES</h2>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Technical Sync"])
    choice = st.radio("Navigation", ["🚀 Meeting Summary", "📅 Meeting Archives"], label_visibility="collapsed")

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 Meeting Summary":
    st.markdown(f"""
    <div class="hero-banner">
        <div style="margin-bottom: 1.5rem;">
            <img src="https://images.unsplash.com/photo-1616531770192-6eaea74c2456?auto=format&fit=crop&q=60&w=1200" 
                 style="border-radius:12px; max-width:600px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);"/>
        </div>
        <h1>Strategic Intelligence Assistant</h1>
        <h2>{m_type} Mode Active</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    title = st.text_input("Session Title", placeholder="e.g., Roadmap Planning")
    
    if file and st.button("Generate Intelligence Report", type="primary", use_container_width=True):
        if not title:
            st.warning("Please specify a session title.")
        else:
            with st.spinner("Decoding Meeting Context..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                    tmp.write(file.getvalue())
                    raw_text = transcribe_long_audio(tmp.name)
                
                # Action items
                p = r"([^.]*(?:homework|assignment|deadline|will|must|due|by|tasked|decided)[^.]*\.)"
                actions = "\n".join([f"• {a.strip()}" for a in re.findall(p, raw_text, re.I)])

                # Summarization (BART)
                tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
                s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
                inputs = tokenizer("summarize: " + raw_text[:3000], return_tensors="pt", max_length=1024, truncation=True)
                sum_ids = s_model.generate(inputs["input_ids"], max_length=150)
                summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

                st.session_state.update({
                    'summary': summary, 
                    'actions': actions, 
                    'current_transcript': raw_text, 
                    'title_saved': title
                })
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- RESULTS DISPLAY ---
    if 'summary' in st.session_state:
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""<div style="background-color: #EBF5FF; padding: 20px; border-radius: 10px; border-left: 5px solid #3B82F6; min-height: 250px;">
                <h4 style="color: #1E40AF; margin-top: 0;">📝 Executive Summary</h4>
                <p style="color: #1E3A8A;">{st.session_state['summary']}</p></div>""", unsafe_allow_html=True)

        with col2:
            act_text = st.session_state.get('actions', 'No actions detected.').replace('•', '<br>•')
            st.markdown(f"""<div style="background-color: #F0FDF4; padding: 20px; border-radius: 10px; border-left: 5px solid #22C55E; min-height: 250px;">
                <h4 style="color: #166534; margin-top: 0;">🚀 Key Deliverables</h4>
                <div style="color: #14532D;">{act_text}</div></div>""", unsafe_allow_html=True)

        # --- CHATBOT SECTION ---
        st.markdown("---")
        st.markdown("### 🤖 Chat with AI Assistant")
        if "messages" not in st.session_state: st.session_state.messages = []
        
        chat_container = st.container(height=350)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])

        if p := st.chat_input("Ask about the meeting..."):
            st.session_state.messages.append({"role": "user", "content": p})
            with chat_container:
                with st.chat_message("user"): st.markdown(p)
                with st.chat_message("assistant"):
                    ans = ask_ai_assistant(st.session_state['current_transcript'], p)
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})

# --- ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown('<div class="hero-banner" style="padding:2rem;"><h1>Archives Center</h1></div>', unsafe_allow_html=True)
