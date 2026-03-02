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

# --- 1. DATABASE SYSTEM (Stable Version) ---
def init_db():
    conn = sqlite3.connect('strategic_intel_final.db')
    c = conn.cursor()
    # Adding 'type' column for your Corporate/Academic classification
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, type TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

def delete_meeting(meeting_id):
    conn = sqlite3.connect('strategic_intel_final.db')
    c = conn.cursor()
    c.execute("DELETE FROM archives WHERE id=?", (meeting_id,))
    conn.commit()
    conn.close()

init_db()

# --- 2. PREMIUM UI/UX CONFIG ---
st.set_page_config(page_title="Strategic Meeting Intelligence", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    .main-title { color: #1E2A38; font-size: 2.8rem; font-weight: 800; margin-bottom: 2rem; }
    .executive-card {
        background: white; padding: 2rem; border-radius: 12px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem; color: #1E293B;
    }
    .badge {
        padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;
        text-transform: uppercase; margin-left: 10px;
    }
    .badge-corp { background: #E0E7FF; color: #4338CA; }
    .badge-edu { background: #DCFCE7; color: #15803D; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAVIGATION ---
with st.sidebar:
    st.markdown("## ⚙️ Workspace")
    meeting_type = st.selectbox("Meeting Type", 
                                ["Corporate Meeting", "Academic Class", "Webinar", "Strategy Sync"])
    st.markdown("---")
    choice = st.radio("Navigation", ["🚀 New Analysis", "📅 Meeting Archives", "💬 Strategic Advisor"])

# --- TAB: MEETING ARCHIVES (Fixed View) ---
if choice == "📅 Meeting Archives":
    st.markdown("<h1 class='main-title'>Intelligence Archives</h1>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('strategic_intel_final.db')
    # Fetching all columns to ensure nothing is blank
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("Archives are currently empty. Please process a meeting in the 'New Analysis' tab.")
    else:
        for row in data:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([4, 1.5, 0.5])
            
            with col1:
                # Badge color logic
                badge_class = "badge-edu" if "Academic" in str(row[3]) else "badge-corp"
                st.markdown(f"### {row[2]} <span class='badge {badge_class}'>{row[3]}</span>", unsafe_allow_html=True)
                st.caption(f"📅 Logged on: {row[1]}")
                
            with col2:
                if st.button("View Details", key=f"v_{row[0]}"):
                    st.session_state[f"show_{row[0]}"] = not st.session_state.get(f"show_{row[0]}", False)
            
            with col3:
                if st.button("🗑️", key=f"d_{row[0]}"):
                    delete_meeting(row[0])
                    st.rerun() # Refresh page after delete

            # Expandable Section for Summary & Actions
            if st.session_state.get(f"show_{row[0]}", False):
                st.markdown("---")
                edit_sum = st.text_area("Edit Summary", row[4], height=150, key=f"es_{row[0]}")
                edit_act = st.text_area("Edit Actions", row[5], height=150, key=f"ea_{row[0]}")
                if st.button("Save Changes", key=f"s_{row[0]}"):
                    c = conn.cursor()
                    c.execute("UPDATE archives SET summary=?, actions=? WHERE id=?", (edit_sum, edit_act, row[0]))
                    conn.commit()
                    st.toast("Record Synchronized!")
            st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- TAB: NEW ANALYSIS (Ensure Data Saves Correctly) ---
elif choice == "🚀 New Analysis":
    st.markdown(f"<h1 class='main-title'>{meeting_type} Suite</h1>", unsafe_allow_html=True)
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    
    file = st.file_uploader("Upload Recording", type=["mp3", "wav", "mp4", "m4a"])
    m_title = st.text_input("Meeting Subject", placeholder="e.g. Sprint Planning")
    
    if file and st.button("🚀 Process Intelligence"):
        with st.spinner("AI is synthesizing..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # AI Processing
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Contextual patterns
            p = r"([^.]*(?:will|must|deadline|homework|assignment|submit|by|due)[^.]*\.)"
            actions = "\n".join([a.strip() for a in re.findall(p, raw_text, re.I)])

            # Summarization
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # SAVE TO DATABASE (Crucial for Archives)
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel_final.db')
            conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                         (ts, m_title, meeting_type, summary, actions, raw_text))
            conn.commit()
            conn.close()
            st.success("Intelligence recorded! Check 'Meeting Archives' tab.")
    st.markdown('</div>', unsafe_allow_html=True)
