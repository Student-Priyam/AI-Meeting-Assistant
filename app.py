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

# --- 1. SYSTEM & DATABASE ---
def init_db():
    conn = sqlite3.connect('strategic_intel_v7.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, type TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. ADAPTIVE UI STYLING ---
st.set_page_config(page_title="Strategic Intel", layout="wide", page_icon="💼")

def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC !important; }
        .executive-card {
            background: white; padding: 2.5rem; border-radius: 16px;
            border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            margin-bottom: 2rem; color: #1E293B;
        }
        .ai-bubble {
            background-color: #F1F5F9; border-left: 5px solid #4F7CFF;
            padding: 1.2rem; border-radius: 12px; margin: 10px 0;
        }
        .edu-theme { border-left: 8px solid #10B981 !important; } /* Green for Education */
        .corp-theme { border-left: 8px solid #4F7CFF !important; } /* Blue for Corporate */
        </style>
        """, unsafe_allow_html=True)

apply_custom_css()

# --- 3. SMART SPEAKER & RECIPIENT LOGIC ---
def extract_contextual_tasks(text, meeting_type):
    # Identifying: Speaker -> Action -> Recipient/Target
    # Patterns for assignments like "Rahul will send the report to Sarah"
    sentences = text.split('.')
    extracted = []
    
    # Base patterns for Corporate vs Academic
    if "Academic" in meeting_type or "Class" in meeting_type:
        patterns = r"([^.]*(?:homework|assignment|read|submit|chapter|test|exam|monday|friday)[^.]*\.)"
    else:
        patterns = r"([^.]*(?:will|must|deadline|by|due|tasked|finalize|send to)[^.]*\.)"
        
    found = re.findall(patterns, text, re.I)
    return "\n".join([f"• {f.strip()}" for f in found])

# --- 4. NAVIGATION & WORKSPACE SETTINGS ---
with st.sidebar:
    st.markdown("## ⚙️ Workspace Settings")
    meeting_type = st.selectbox("Meeting Classification", 
                                ["Corporate Board Meeting", "Academic Lecture/Online Class", 
                                 "Product Strategy Sync", "Public Webinar", "Technical Workshop"])
    
    st.markdown("---")
    mode = st.sidebar.radio("Navigation", ["🚀 Intelligence Suite", "📅 Archives", "💬 Strategic Advisor"])
    st.caption(f"Mode: {meeting_type}")

# --- TAB 1: INTELLIGENCE SUITE (Video/Audio) ---
if mode == "🚀 Intelligence Suite":
    theme_class = "edu-theme" if "Academic" in meeting_type else "corp-theme"
    
    st.markdown(f'<h1 style="color:#1E2A38;">{meeting_type} Analysis</h1>', unsafe_allow_html=True)
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    
    file = st.file_uploader("Upload Recording (Video or Audio)", type=["mp3", "wav", "mp4", "m4a", "mov"])
    
    if file:
        if file.type.startswith('video'):
            st.video(file) # Video Preview
        else:
            st.audio(file)
            
    title = st.text_input("Session Title", placeholder="e.g. History Lecture 01 or Sprint Planning")
    
    if file and st.button("🚀 Process Intelligence"):
        with st.spinner("AI is analyzing speakers and strategic intent..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # AI Analysis (Whisper extracts audio from video natively)
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Contextual Extraction (Who to Whom / Task)
            actions = extract_contextual_tasks(raw_text, meeting_type)

            # Summarization
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # Save with Type
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel_v7.db')
            conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                         (ts, title, meeting_type, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.success("Analysis Optimized for " + meeting_type)
            
            # Adaptive Display
            col1, col2 = st.columns(2)
            with col1:
                header = "📚 Core Concepts" if "Academic" in meeting_type else "📄 Executive Summary"
                st.markdown(f"**{header}**")
                st.info(summary)
            with col2:
                header = "📝 Assignments/Deadlines" if "Academic" in meeting_type else "🎯 Action Items"
                st.markdown(f"**{header}**")
                st.success(actions if actions else "No specific items detected.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 3: STRATEGIC ADVISOR (Knowledge Base) ---
elif mode == "💬 Strategic Advisor":
    st.markdown('<h1 style="color:#1E2A38;">Strategic Advisor</h1>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_v7.db')
    rows = conn.execute("SELECT title, transcript, type FROM archives").fetchall()
    options = {f"{r[0]} ({r[2]})": r[1] for r in rows}
    
    if options:
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        sel = st.selectbox("Choose Session Context", list(options.keys()))
        query = st.text_input("Ask a question (e.g., What did the professor say about the exam? or What is Rahul's task?)")
        
        if query:
            context = options[sel]
            # Pinpoint Search Logic
            matches = [s.strip() for s in context.split('.') if any(w.lower() in s.lower() for w in query.split())]
            
            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                st.write(f"**Advisor Response:** Based on the recording, {'. '.join(matches[:2])}.")
            else:
                st.write("**Advisor Response:** I couldn't find a direct reference. Try broader keywords.")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    conn.close()
