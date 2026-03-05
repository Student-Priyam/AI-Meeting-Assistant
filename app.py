# --- 1. PYTHON 3.13 COMPATIBILITY SHIM ---
try:
    import audioop
except ImportError:
    import audioop_lts as audioop
    import sys
    sys.modules['audioop'] = audioop

import streamlit as st
import whisper
import requests  # Added for stable direct API calls
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import re
import os
import sqlite3
import tempfile
from datetime import datetime
from pydub import AudioSegment  
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

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

# --- 2.1 STABLE DIRECT CHATBOT LOGIC ---
def ask_gemini_direct(transcript, user_query):
    if "GEMINI_API_KEY" not in st.secrets:
        return "Error: API Key missing in Secrets."
    
    api_key = st.secrets["GEMINI_API_KEY"]
    
    # CHANGED: v1beta to v1 AND models/gemini-1.5-flash to gemini-1.5-flash
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Context: {transcript}\n\nQuestion: {user_query}\n\nAnswer strictly based on the context."
            }]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # Agar ab bhi error aaye toh ye exact error message dikhayega
            return f"AI Error {response.status_code}: {response.text}"
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

    div[data-baseweb="select"] > div {
        background-color: white !important;
        color: #0F172A !important; 
        border-radius: 8px;
    }
    ul[data-baseweb="menu"] li { color: #0F172A !important; }

    .hero-banner {
        background: linear-gradient(135deg, #005A92 0%, #00426d 100%);
        padding: 3rem 2rem;
        border-radius: 16px;
        margin-bottom: 2.5rem;
        color: white;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .hero-banner h1 { font-size: 2.8rem; font-weight: 700; margin-bottom: 0.5rem; color: white !important; }
    .hero-banner h2 { font-size: 1.5rem; font-weight: 400; color: #E0E7FF !important; }

    .executive-card {
        background: white; padding: 2.5rem; border-radius: 12px; border: 1px solid #E2E8F0; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1.5rem; 
    }
</style>
""", unsafe_allow_html=True)

# --- 4. LONG-FORM AUDIO PROCESSING ---
def transcribe_long_audio(file_path):
    model = whisper.load_model("base")
    audio = AudioSegment.from_file(file_path)
    chunk_length = 5 * 60 * 1000 
    chunks = [audio[i:i + chunk_length] for i in range(0, len(audio), chunk_length)]
    full_transcript = ""
    progress_bar = st.progress(0)
    for i, chunk in enumerate(chunks):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_chunk:
            chunk.export(tmp_chunk.name, format="wav")
            result = model.transcribe(tmp_chunk.name)
            full_transcript += result["text"] + " "
            os.remove(tmp_chunk.name)
        progress_bar.progress((i + 1) / len(chunks))
    return full_transcript

# --- 5. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='text-align:center; font-weight:700;'>STRATEGIC MINUTES</h2>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Technical Sync"])
    choice = st.radio("Navigation", ["🚀 Meeting Summary", "📅 Meeting Archives"], label_visibility="collapsed")

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 Meeting Summary":
    st.markdown(f"""
    <div class="hero-banner">
        <div style="margin-bottom: 1.5rem;">
            <img src="https://images.unsplash.com/photo-1616531770192-6eaea74c2456?auto=format&fit=crop&q=60&w=1200" 
                 style="border-radius:12px; max-width:600px; shadow: 0 4px 15px rgba(0,0,0,0.3);"/>
        </div>
        <h1>Missed a meeting? No need to rewatch it.</h1>
        <h2>{m_type} Intelligence Mode</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    title = st.text_input("Session Title", placeholder="e.g., Q1 Roadmap Planning")
    
    if file and st.button("Generate Meeting Summary", type="primary", use_container_width=True):
        if not title:
            st.warning("Please specify a session title.")
        else:
            with st.spinner("Decoding Context..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                    tmp.write(file.getvalue())
                    tmp_path = tmp.name

                raw_text = transcribe_long_audio(tmp_path)
                os.remove(tmp_path)

                st.session_state['current_transcript'] = raw_text
                
                # Extraction
                p = r"([^.]*(?:homework|assignment|deadline|will|must|due|by|tasked|decided)[^.]*\.)"
                actions = "\n".join([f"• {a.strip()}" for a in re.findall(p, raw_text, re.I)])

                # Summarization
                tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
                s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
                inputs = tokenizer("summarize: " + raw_text[:3500], return_tensors="pt", max_length=1024, truncation=True)
                sum_ids = s_model.generate(inputs["input_ids"], max_length=200, min_length=80)
                summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

                ts = datetime.now().strftime("%d-%m-%Y %H:%M")
                conn = sqlite3.connect('strategic_intel_v8.db')
                conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                             (ts, title, m_type, summary, actions, raw_text))
                conn.commit()
                conn.close()

                st.session_state.update({'summary': summary, 'actions': actions, 'ts': ts, 'active_mode': m_type, 'title_saved': title})
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if 'summary' in st.session_state:
        st.divider()
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("#### 📝 Executive Summary")
            st.info(st.session_state['summary'])

        with col2:
            st.markdown("#### 🚀 Key Deliverables")
            st.success(st.session_state['actions'] if st.session_state['actions'] else "No specific actions detected.")

        # --- CHATBOT SECTION (Direct Request Method) ---
        st.markdown("---")
        st.markdown("### 🤖 Chat with AI Assistant")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        chat_container = st.container(height=300)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Ask about this session..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    # Using the stable direct bypass function
                    answer = ask_gemini_direct(st.session_state['current_transcript'], prompt)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

        st.divider()
        st.download_button("📥 Download Report (.txt)", f"Report: {st.session_state.get('title_saved')}\n\n{st.session_state['summary']}", use_container_width=True)

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown('<div class="hero-banner"><h1>Archives Center</h1></div>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_v8.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    if not data: st.info("Historical archives are currently empty.")
    else:
        for row in data:
            with st.expander(f"📅 {row[1]} | {row[2]} ({row[3]})"):
                st.write(f"**Summary:** {row[4]}")
                st.write(f"**Action Items:** {row[5]}")
                if st.button("Delete", key=f"d_{row[0]}"): 
                    delete_record(row[0]); st.rerun()
    conn.close()

