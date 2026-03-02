import streamlit as st
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import re
import os
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- 1. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS meeting_history 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. PDF GENERATOR ---
def create_pdf(title, summary, actions, date):
    pdf_path = f"Meeting_Minutes_{date}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "OFFICIAL MEETING MINUTES")
    c.setFont("Helvetica", 12)
    c.drawString(100, 730, f"Date: {date}")
    c.drawString(100, 715, f"Subject: {title}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 680, "Executive Summary:")
    c.setFont("Helvetica", 11)
    text_obj = c.beginText(100, 660)
    text_obj.textLines(summary[:1000]) # Simplified for brevity
    c.drawText(text_obj)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 500, "Action Items:")
    c.setFont("Helvetica", 11)
    y = 480
    for item in actions.split('\n'):
        c.drawString(120, y, f"• {item}")
        y -= 15
    c.save()
    return pdf_path

# --- 3. UI CONFIG & STYLING ---
st.set_page_config(page_title="Strategic Meeting Intelligence", layout="wide")

# High-End UX with Background Image
st.markdown("""
    <style>
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1517245318773-b7b83ca927a0?auto=format&fit=crop&q=80&w=2070");
        background-size: cover;
    }
    .glass-morphism {
        background: rgba(255, 255, 255, 0.85);
        padding: 30px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.18);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. MODELS ---
@st.cache_resource
def load_models():
    w_model = whisper.load_model("base")
    tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
    s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
    return w_model, tokenizer, s_model

w_model, tokenizer, s_model = load_models()

# --- 5. APP TABS ---
menu = ["🎙️ New Meeting", "📅 History & Edit", "💬 Meeting Chatbot"]
choice = st.sidebar.selectbox("Navigation", menu)

# --- TAB 1: NEW MEETING ---
if choice == "🎙️ New Meeting":
    st.markdown('<div class="glass-morphism">', unsafe_allow_html=True)
    st.title("💼 Enterprise Meeting Intelligence")
    
    audio_file = st.file_uploader("Upload Recording (Audio/Video)", type=["mp3", "wav", "mp4"])
    meeting_title = st.text_input("Meeting Title", placeholder="e.g. Q1 Budget Planning")
    
    if audio_file and st.button("🚀 Analyze & Save"):
        with st.spinner("Processing..."):
            # Transcription & Date Detection
            result = w_model.transcribe(audio_file.name)
            raw_text = result["text"]
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Smart Logic for Actions (Regex based for dates/deadlines)
            action_items = "\n".join(re.findall(r"([^.]*(?:will|need to|deadline|by|must)[^.]*\.)", raw_text, re.I))
            
            # Summary
            inputs = tokenizer("summarize: " + raw_text[:2000], return_tensors="pt", max_length=1024, truncation=True)
            summary_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            
            # Save to Database
            conn = sqlite3.connect('meetings.db')
            c = conn.cursor()
            c.execute("INSERT INTO meeting_history (date, title, summary, actions, transcript) VALUES (?,?,?,?,?)",
                      (today, meeting_title, summary, action_items, raw_text))
            conn.commit()
            conn.close()
            
            st.success("Meeting Analyzed and Saved to Database!")
            
            # PDF Generation
            pdf_file = create_pdf(meeting_title, summary, action_items, today)
            with open(pdf_file, "rb") as f:
                st.download_button("📥 Download Official PDF", f, file_name=pdf_file)
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: HISTORY & EDIT ---
elif choice == "📅 History & Edit":
    st.title("📅 Meeting Archives")
    conn = sqlite3.connect('meetings.db')
    df = conn.execute("SELECT * FROM meeting_history").fetchall()
    
    for row in df:
        with st.expander(f"{row[1]} | {row[2]}"):
            new_summary = st.text_area("Edit Summary", row[3], key=f"sum_{row[0]}")
            new_actions = st.text_area("Edit Actions", row[4], key=f"act_{row[0]}")
            if st.button("Update Database", key=f"btn_{row[0]}"):
                c = conn.cursor()
                c.execute("UPDATE meeting_history SET summary=?, actions=? WHERE id=?", (new_summary, new_actions, row[0]))
                conn.commit()
                st.toast("Updated successfully!")
    conn.close()

# --- TAB 3: CHATBOT ---
elif choice == "💬 Meeting Chatbot":
    st.title("💬 Ask anything about your meetings")
    conn = sqlite3.connect('meetings.db')
    titles = [r[0] for r in conn.execute("SELECT title FROM meeting_history").fetchall()]
    selected_meeting = st.selectbox("Select Meeting to Discuss", titles)
    
    user_ques = st.text_input("Ask a question (e.g., What was the final decision?)")
    if user_ques:
        transcript = conn.execute("SELECT transcript FROM meeting_history WHERE title=?", (selected_meeting,)).fetchone()[0]
        # Simple Semantic Search (Logic: Find sentences containing user keywords)
        relevant_info = [s for s in transcript.split('.') if any(w in s.lower() for w in user_ques.lower().split())]
        st.info(f"AI Response: Based on the meeting, {' '.join(relevant_info[:2])}")
