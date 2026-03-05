# --- 1. PYTHON 3.13 COMPATIBILITY SHIM ---
try:
    import audioop
except ImportError:
    import audioop_lts as audioop
    import sys
    sys.modules['audioop'] = audioop

import streamlit as st
import whisper
import google.generativeai as genai  # FOR CHATBOT
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

# --- 2.1 AI CONFIGURATION (FOR CHATBOT) ---
# Ensure "GEMINI_API_KEY" is added in Streamlit Cloud Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 'models/' prefix hata kar direct try karein agar library update kar di hai toh
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("⚠️ API Key missing! Go to Settings > Secrets and add GEMINI_API_KEY.")

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

# --- 4. LONG-FORM AUDIO PROCESSING (CHUNKING) ---
def transcribe_long_audio(file_path):
    model = whisper.load_model("base")
    audio = AudioSegment.from_file(file_path)
    
    # 5-minute chunks
    chunk_length = 5 * 60 * 1000 
    chunks = [audio[i:i + chunk_length] for i in range(0, len(audio), chunk_length)]
    
    full_transcript = ""
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, chunk in enumerate(chunks):
        progress_text.text(f"Processing segment {i+1} of {len(chunks)}...")
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
    st.markdown("<hr style='border-color:#334155'>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Technical Sync"])
    st.markdown("---")
    choice = st.radio("Navigation", ["🚀 Meeting Summary", "📅 Meeting Archives"], label_visibility="collapsed")

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 Meeting Summary":
    st.markdown(f"""
    <div class="hero-banner">
        <div style="margin-bottom: 1.5rem;">
            <img src="https://images.unsplash.com/photo-1616531770192-6eaea74c2456?auto=format&fit=crop&q=60&w=1200" 
                 style="border-radius:12px; max-width:600px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);"/>
        </div>
        <h1>Missed a meeting? No need to rewatch it.</h1>
        <h2>{m_type} Intelligence Mode</h2>
        <p>Optimized for long-form sessions up to 60 minutes.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    title = st.text_input("Session Title", placeholder="e.g., Q1 Roadmap Planning")
    
    if file and st.button("Generate Meeting Summary", type="primary", use_container_width=True):
        if not title:
            st.warning("Please specify a session title.")
        else:
            with st.spinner(f"Decoding long-form {m_type} context..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                    tmp.write(file.getvalue())
                    tmp_path = tmp.name

                raw_text = transcribe_long_audio(tmp_path)
                os.remove(tmp_path)

                st.session_state['current_transcript'] = raw_text
                
                # Action items extraction
                p = r"([^.]*(?:homework|assignment|deadline|will|must|due|by|tasked|decided)[^.]*\.)"
                actions = "\n".join([f"• {a.strip()}" for a in re.findall(p, raw_text, re.I)])

                # Summarization (BART)
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

                st.session_state['summary'] = summary
                st.session_state['actions'] = actions
                st.session_state['ts'] = ts
                st.session_state['active_mode'] = m_type
                st.session_state['title_saved'] = title
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- RESULTS SECTION ---
    if 'summary' in st.session_state:
        st.divider()
        st.markdown(f"### 🎯 Strategic Insights: {st.session_state.get('active_mode', m_type)}")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"""
            <div style="background-color: #EBF5FF; padding: 20px; border-radius: 10px; border-left: 5px solid #3B82F6; height: 100%;">
                <h4 style="color: #1E40AF; margin-top: 0;">📝 Executive Summary</h4>
                <p style="color: #1E3A8A; line-height: 1.6;">{st.session_state['summary']}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            raw_actions = st.session_state['actions'].split('•')
            clean_actions = "".join([f"<li style='margin-bottom: 8px;'>{a.strip()}</li>" for a in raw_actions if len(a.strip()) > 10])
            st.markdown(f"""
            <div style="background-color: #F0FDF4; padding: 20px; border-radius: 10px; border-left: 5px solid #22C55E; height: 100%;">
                <h4 style="color: #166534; margin-top: 0;">🚀 Key Deliverables</h4>
                <ul style="color: #14532D; padding-left: 20px; line-height: 1.5;">
                    {clean_actions}
                </ul>
            </div>
            """, unsafe_allow_html=True)

        # --- SMART CHATBOT SECTION ---
        st.markdown("---")
        st.markdown("### 🤖 Chat with AI Assistant")
        st.caption("Aap is meeting ke context mein koi bhi sawal puch sakte hain.")

        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Chat display container
        chat_container = st.container(height=350)
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
                    # Context prompt for high accuracy
                    context_query = f"""
                    Transcript: {st.session_state['current_transcript']}
                    
                    User Question: {prompt}
                    
                    Instruction: Answer strictly based on the transcript provided. If you cannot find the answer, say you don't know.
                    """
                    try:
                        response = gemini_model.generate_content(context_query)
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        # DEBUG: Ye line aapko batayegi ki problem kya hai
                        st.error(f"AI Error: {e}")

        # --- DOWNLOAD REPORT ---
        st.divider()
        report_content = f"STRATEGIC INTELLIGENCE REPORT\nTITLE: {st.session_state.get('title_saved')}\nDATE: {st.session_state['ts']}\n\nSUMMARY:\n{st.session_state['summary']}\n\nTRANSCRIPT:\n{st.session_state['current_transcript']}"
        st.download_button(
            label="📥 Download Full Report (.txt)",
            data=report_content,
            file_name=f"Report_{st.session_state.get('title_saved')}.txt",
            mime="text/plain",
            use_container_width=True
        )

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown('<div class="hero-banner" style="padding: 2rem;"><h1>Archives Center</h1></div>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_v8.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    if not data: 
        st.info("Historical archives are currently empty.")
    else:
        for row in data:
            with st.expander(f"📅 {row[1]} | {row[2]} ({row[3]})"):
                st.write(f"**Summary:** {row[4]}")
                st.write(f"**Action Items:** {row[5]}")
                if st.button("Delete", key=f"d_{row[0]}"): 
                    delete_record(row[0])
                    st.rerun()
    conn.close()




