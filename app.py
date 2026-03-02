# --- 1. PYTHON 3.13 COMPATIBILITY SHIM ---
try:
    import audioop
except ImportError:
    import audioop_lts as audioop
    import sys
    sys.modules['audioop'] = audioop

import streamlit as st
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
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
    # Updated table to ensure transcript is always retrievable
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
        padding: 2rem; border-radius: 16px; margin-bottom: 2rem; color: white; text-align: center;
    }
    .chat-bubble {
        padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #E2E8F0;
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
    st.markdown("<h2 style='text-align:center;'>STRATEGIC MINUTES</h2>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Technical Sync"])
    choice = st.radio("Navigation", ["🚀 Meeting Summary", "💬 Chat with Audio", "📅 Meeting Archives"])

# --- TAB 1: SUMMARY GENERATION ---
if choice == "🚀 Meeting Summary":
    st.markdown('<div class="hero-banner"><h1>Intelligence Mode</h1><p>Upload your session to generate insights.</p></div>', unsafe_allow_html=True)
    
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a"])
    title = st.text_input("Session Title")
    
    if file and st.button("Generate Meeting Summary", type="primary"):
        with st.spinner("Processing..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            raw_text = transcribe_long_audio(tmp_path)
            os.remove(tmp_path)

            # Extraction & Summary Logic
            p = r"([^.]*(?:homework|assignment|deadline|will|must|due|by|tasked|decided)[^.]*\.)"
            actions = "\n".join([f"• {a.strip()}" for a in re.findall(p, raw_text, re.I)])
            
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:3500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=200)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel_v8.db')
            conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                         (ts, title, m_type, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.session_state['current_transcript'] = raw_text
            st.session_state['summary'] = summary
            st.success("Summary Generated! Navigate to 'Chat with Audio' to ask questions.")

# --- TAB 2: CHATBOT SYSTEM ---
elif choice == "💬 Chat with Audio":
    st.markdown('<div class="hero-banner"><h1>Meeting Concierge</h1><p>Ask anything about your recorded sessions.</p></div>', unsafe_allow_html=True)

    # Fetch available sessions from DB
    conn = sqlite3.connect('strategic_intel_v8.db')
    sessions = conn.execute("SELECT id, title, transcript FROM archives ORDER BY id DESC").fetchall()
    conn.close()

    if not sessions:
        st.warning("No sessions found. Please upload and process an audio file first.")
    else:
        session_map = {f"{s[1]} (ID: {s[0]})": s[2] for s in sessions}
        selected_session = st.selectbox("Select a session to chat with:", list(session_map.keys()))
        context_text = session_map[selected_session]

        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display Chat History
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("What was discussed regarding the budget?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Reviewing transcript..."):
                    # QA Pipeline
                    # We use a smaller context window around the answer for performance
                    qa_model = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
                    
                    # To handle long transcripts, we pass the first 3000 chars or implement a search
                    # For a basic shim, we'll use the first chunk of text
                    result = qa_model(question=prompt, context=context_text[:3000])
                    
                    response = f"Based on the transcript: {result['answer']}"
                    if result['score'] < 0.1:
                        response = "I couldn't find a definitive answer in the transcript. Could you try rephrasing?"
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

# --- TAB 3: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown('<div class="hero-banner"><h1>Archives</h1></div>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_v8.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    for row in data:
        with st.expander(f"📅 {row[1]} | {row[2]}"):
            st.write(f"**Summary:** {row[4]}")
            if st.button("Delete", key=f"d_{row[0]}"):
                delete_record(row[0]); st.rerun()
    conn.close()
