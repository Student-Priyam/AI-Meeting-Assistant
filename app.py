import streamlit as st
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import re
import os
import sqlite3
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# --- 1. CORE DATABASE SYSTEM ---
def init_db():
    conn = sqlite3.connect('strategic_intel_final.db')
    c = conn.cursor()
    # Schema includes 'type' for classification
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, type TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

def delete_record(record_id):
    conn = sqlite3.connect('strategic_intel_final.db')
    conn.execute("DELETE FROM archives WHERE id=?", (record_id,))
    conn.commit()
    conn.close()

init_db()

# --- 2. PREMIUM UI/UX CONFIG (THE ABSOLUTE FIX) ---
st.set_page_config(page_title="Strategic Intel | AI Meeting Assistant", layout="wide", page_icon="💼")

# THE FIX: Using a single, clean block for CSS to stop the text leak
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; color: white !important; }
    .hero-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 3rem 2rem; border-radius: 16px; margin-bottom: 2.5rem; color: white;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1); text-align: center;
    }
    .executive-card {
        background: white; padding: 2rem; border-radius: 12px; border: 1px solid #E2E8F0; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1.5rem; 
    }
    .ai-bubble {
        background-color: #F1F5F9; border-left: 4px solid #3b82f6; padding: 1.25rem; 
        border-radius: 0 12px 12px 0; margin: 1rem 0; color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>STRATEGIC INTEL</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#334155'>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Type", ["Corporate Meeting", "Academic Class", "Strategy Sync"])
    choice = st.radio("Navigation", ["🚀 Intelligence Suite", "📅 Meeting Archives"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("v8.0 Enterprise Edition")

# --- TAB 1: INTELLIGENCE SUITE + PINPOINT QUERY ---
if choice == "🚀 Intelligence Suite":
    st.markdown("""
    <div class="hero-banner">
        <h1>Missed a meeting? No need to rewatch it.</h1>
        <p>Upload your recording. We'll extract insights and answer your questions instantly.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    title = st.text_input("Session Title", placeholder="e.g., Q1 Roadmap Sync")
    
    if file:
        if file.type.startswith('video'): st.video(file) # Full video support
        else: st.audio(file)
                
    if st.button("🚀 Process Intelligence", type="primary", use_container_width=True):
        with st.spinner("Decoding meeting context..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Store in session state
            st.session_state['current_transcript'] = raw_text

            # Adaptive context extraction patterns
            p = r"([^.]*(?:monday|friday|deadline|will|must|homework|assignment|submit|due|by|tasked|decided)[^.]*\.)"
            actions = "\n".join([f"• {a.strip()}" for a in re.findall(p, raw_text, re.I)])

            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel_final.db')
            conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                         (ts, title, m_type, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.session_state['summary'] = summary
            st.session_state['actions'] = actions
            st.session_state['ts'] = ts
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if 'summary' in st.session_state:
        st.divider()
        st.subheader("Executive Synthesis")
        c1, c2 = st.columns(2)
        # Adaptive UI labels
        with c1: st.info(f"**{ '📚 Concepts' if 'Academic' in m_type else '📄 Summary' }:**\n\n{st.session_state['summary']}")
        with c2: st.success(f"**{ '📝 Assignments' if 'Academic' in m_type else '🎯 Actions' }:**\n\n{st.session_state['actions']}")

        st.divider()
        st.subheader("💬 Query Session Context")
        user_q = st.text_input("Ask about Rahul's role, deadlines, or specific decisions...", key="live_query_box")
        if user_q:
            ctx = st.session_state['current_transcript']
            # Pinpoint search logic
            sentences = [s.strip() for s in ctx.split('.') if len(s.strip()) > 5]
            query_words = [w.lower() for w in user_q.split() if len(w) > 3]
            matches = [s for s in sentences if any(w in s.lower() for w in query_words)]

            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                # Returns specific data found, skipping intro
                st.write(f"**Advisor Response:** Based on the transcript: *{'. '.join(matches[:2])}*")
            else:
                st.write("**Advisor Response:** I could not find a specific mention of that in this session.")
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown('<div class="hero-banner" style="padding: 1.5rem;"><h1>Archives</h1></div>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_final.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    if not data: st.info("No records found.")
    else:
        for row in data:
            with st.expander(f"📅 {row[1]} | {row[2]} ({row[3]})"):
                st.markdown(f"**Summary:** {row[4]}")
                st.markdown(f"**Action Items:** {row[5]}")
                if st.button("Delete", key=f"d_{row[0]}"): 
                    delete_record(row[0])
                    st.rerun()
    conn.close()
