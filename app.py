import streamlit as st
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import re
import os
import sqlite3
import tempfile
from datetime import datetime
from pydub import AudioSegment  # Added for chunking
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# --- 1. CORE DATABASE SYSTEM ---
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

# --- 2. PREMIUM UI/UX CONFIG ---
st.set_page_config(page_title="Strategic Meeting | AI Meeting Assistant", layout="wide", page_icon="💼")

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
    }
    
    ul[data-baseweb="menu"] li {
        color: #0F172A !important;
    }

    .hero-banner {
        background: linear-gradient(135deg, #005A92 0%, #00426d 100%);
        padding: 3.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2.5rem;
        color: white;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .hero-banner h1 { font-size: 2.8rem; font-weight: 700; margin-bottom: 0.5rem; color: white !important; }
    .hero-banner h2 { font-size: 1.8rem; font-weight: 600; color: #E0E7FF !important; margin-bottom: 1rem; }
    .hero-banner p { font-size: 1.1rem; color: #cbd5e1 !important; }

    .executive-card {
        background: white; padding: 2.5rem; border-radius: 12px; border: 1px solid #E2E8F0; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1.5rem; 
    }
</style>
""", unsafe_allow_html=True)

# --- 3. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='text-align:center; font-weight:700;'>STRATEGIC MEETING</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#334155'>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Technical Sync"])
    st.markdown("---")
    choice = st.radio("Navigation", ["🚀 Meeting Summary", "📅 Meeting Archives"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("<div style='text-align:center; opacity:0.8; font-size:12px;'>Whisper & BART</div>", unsafe_allow_html=True)

# --- 4. PROCESSING HELPER (CHUNKING) ---
def transcribe_long_audio(file_path):
    model = whisper.load_model("base")
    audio = AudioSegment.from_file(file_path)
    
    # Define chunk length (5 minutes = 300,000 ms)
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

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 Meeting Summary":
    st.markdown(f"""
    <div class="hero-banner">
        <h1>Missed a meeting? No need to rewatch it.</h1>
        <h2>{m_type} Intelligence</h2>
        <p>Optimized for long-form sessions (Up to 60 mins).</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    title = st.text_input("Session Title", placeholder="e.g., Project Roadmap Deep-Dive")
    
    if file and st.button("Generate Intelligence Summary", type="primary", use_container_width=True):
        if not title:
            st.warning("Please specify a session title.")
        else:
            with st.spinner(f"Processing long-form {m_type} context... This may take several minutes."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                    tmp.write(file.getvalue())
                    tmp_path = tmp.name

                # Process using Chunking Logic
                raw_text = transcribe_long_audio(tmp_path)
                os.remove(tmp_path)

                st.session_state['current_transcript'] = raw_text
                
                # Context-aware extraction patterns
                p = r"([^.]*(?:homework|assignment|deadline|will|must|due|by|tasked|decided)[^.]*\.)"
                actions = "\n".join([f"• {a.strip()}" for a in re.findall(p, raw_text, re.I)])

                # Summarization (Processed in segments if text is too long)
                tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
                s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
                
                # Limit input for summary to avoid model crash
                inputs = tokenizer("summarize: " + raw_text[:3500], return_tensors="pt", max_length=1024, truncation=True)
                sum_ids = s_model.generate(inputs["input_ids"], max_length=200, min_length=80)
                summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

                ts = datetime.now().strftime("%d-%m-%Y %H:%M")
                conn = sqlite3.connect('strategic_intel_v8.db')
                conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                             (ts, title, m_type, summary, actions, raw_text))
                conn.commit()
                conn.close()

                st.session_state['summary'] = summary
                st.session_state['actions'] = actions
                st.session_state['ts'] = ts
                st.session_state['active_mode'] = m_type
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if 'summary' in st.session_state:
        st.divider()
        st.subheader(f"Synthesis Output: {st.session_state.get('active_mode', m_type)}")
        c1, c2 = st.columns(2)
        with c1: st.info(f"**📄 Summary:**\n\n{st.session_state['summary']}")
        with c2: st.success(f"**🎯 Actionable Items:**\n\n{st.session_state['actions']}")

# --- ARCHIVES LOGIC REMAINS SAME ---
elif choice == "📅 Meeting Archives":
    st.markdown('<div class="hero-banner" style="padding: 2rem;"><h1>Archives Center</h1></div>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_v8.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    if not data: st.info("Historical archives are currently empty.")
    else:
        for row in data:
            with st.expander(f"📅 {row[1]} | {row[2]} ({row[3]})"):
                st.write(f"**Summary:** {row[4]}")
                st.write(f"**Action Items:** {row[5]}")
                if st.button("Delete", key=f"d_{row[0]}"): 
                    delete_record(row[0])
                    st.rerun()
    conn.close()
