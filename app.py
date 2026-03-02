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

# --- 1. DATABASE SYSTEM ---
def init_db():
    conn = sqlite3.connect('meetings_pro.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS meeting_history 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

def delete_meeting(meeting_id):
    conn = sqlite3.connect('meetings_pro.db')
    c = conn.cursor()
    c.execute("DELETE FROM meeting_history WHERE id=?", (meeting_id,))
    conn.commit()
    conn.close()

# --- 2. STABLE PROFESSIONAL PDF GENERATOR ---
def create_pro_pdf(title, summary, actions, date):
    pdf_path = f"MoM_{date.replace(':', '-')}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Using standard colors to prevent hexColor crashes
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=22, textColor=colors.darkblue, spaceAfter=12)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.blue, spaceBefore=15, spaceAfter=10)
    body_style = styles['Normal']

    story.append(Paragraph("STRATEGIC MEETING MINUTES", title_style))
    story.append(Paragraph(f"<b>Subject:</b> {title}", body_style))
    story.append(Paragraph(f"<b>Date:</b> {date}", body_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    story.append(Paragraph(summary, body_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("ACTION ITEMS & DELIVERABLES", heading_style))
    
    # Table Logic
    action_data = [["ID", "Deliverable / Deadline"]]
    for i, item in enumerate(actions.split('\n'), 1):
        if item.strip():
            action_data.append([str(i), item.strip()])

    if len(action_data) > 1:
        t = Table(action_data, colWidths=[40, 440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('TEXTCOLOR', (0,0), (-1,0), colors.darkblue),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t)
    
    doc.build(story)
    return pdf_path

init_db()

# --- 3. UNIQUE PREMIUM UI/UX (Glass-Morphism Dark Theme) ---
st.set_page_config(page_title="Strategic Meeting Intelligence", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), 
                    url("https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=2069");
        background-size: cover;
        background-attachment: fixed;
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 15px 35px rgba(0,0,0,0.5);
        color: #1e293b;
        margin-bottom: 20px;
    }
    .main-title { color: white; font-size: 3rem; font-weight: 800; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
    .stButton>button {
        background-image: linear-gradient(to right, #2563eb, #1e40af);
        color: white; border: none; border-radius: 10px; padding: 0.5rem 2rem;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(37,99,235,0.4); }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>💼 Workspace</h2>", unsafe_allow_html=True)
    choice = st.radio("Go to:", ["🚀 New Intelligence", "📅 Meeting Archives", "💬 AI Consultant"])
    st.markdown("---")
    st.caption("Powered by Enterprise AI v3.0")

# --- TAB 1: NEW INTELLIGENCE ---
if choice == "🚀 New Intelligence":
    st.markdown("<h1 class='main-title'>Strategic Synthesis</h1>", unsafe_allow_html=True)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    audio_file = st.file_uploader("Upload Meeting Audio/Video", type=["mp3", "wav", "mp4", "m4a"])
    m_title = st.text_input("Meeting Subject", placeholder="e.g. Annual Strategy Review")
    
    if audio_file and st.button("Generate Strategic MoM"):
        with st.spinner("Analyzing meeting context..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as tmp:
                tmp.write(audio_file.getvalue())
                tmp_path = tmp.name

            # Transcription
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Smart Intent Extraction
            patterns = r"([^.]*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|will|must|deadline|by|due|schedule|complete|final)[^.]*\.)"
            actions = "\n".join([a.strip() for a in re.findall(patterns, raw_text, re.I)])

            # Summarization
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # DB Save
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('meetings_pro.db')
            conn.execute("INSERT INTO meeting_history (date, title, summary, actions, transcript) VALUES (?,?,?,?,?)",
                         (ts, m_title, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.success("Synthesis complete. Archive updated.")
            pdf_path = create_pro_pdf(m_title, summary, actions, ts)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download Official PDF Minutes", f, file_name=f"{m_title}.pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown("<h1 class='main-title'>Intelligence Repository</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect('meetings_pro.db')
    data = conn.execute("SELECT * FROM meeting_history ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("Repository is empty. Analyze a recording to begin.")
    else:
        for row in data:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([4, 1.5, 0.5])
            with col1:
                st.subheader(f"📌 {row[2]}")
                st.caption(f"📅 Logged on: {row[1]}")
            with col2:
                if st.button("View / Edit", key=f"v_{row[0]}"):
                    st.session_state[f"ed_{row[0]}"] = not st.session_state.get(f"ed_{row[0]}", False)
            with col3:
                if st.button("🗑️", key=f"d_{row[0]}"):
                    delete_meeting(row[0])
                    st.rerun()

            if st.session_state.get(f"ed_{row[0]}", False):
                new_s = st.text_area("Executive Summary", row[3], height=150, key=f"ts_{row[0]}")
                new_a = st.text_area("Action Items", row[4], height=150, key=f"ta_{row[0]}")
                if st.button("Update Database", key=f"s_{row[0]}"):
                    c = conn.cursor()
                    c.execute("UPDATE meeting_history SET summary=?, actions=? WHERE id=?", (new_s, new_a, row[0]))
                    conn.commit()
                    st.toast("Record Synchronized!")
            st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- TAB 3: AI CONSULTANT ---
elif choice == "💬 AI Consultant":
    st.markdown("<h1 class='main-title'>Strategic Advisor</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect('meetings_pro.db')
    recs = {r[2]: r[5] for r in conn.execute("SELECT title, transcript FROM meeting_history").fetchall()}
    
    if recs:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        sel = st.selectbox("Select Contextual Meeting", list(recs.keys()))
        query = st.text_input("Consult with AI about this meeting...")
        if query:
            ctx = recs[sel]
            matches = [s for s in ctx.split('.') if any(w.lower() in s.lower() for w in query.split())]
            if matches:
                st.info(f"**AI Advisor:** {'. '.join(matches[:2])}.")
            else:
                st.warning("No direct reference found. Try using broader keywords.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Archives are currently empty.")
    conn.close()
