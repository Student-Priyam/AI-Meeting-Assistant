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

    # Branding & Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=22, textColor=colors.darkblue, spaceAfter=12)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.blue, spaceBefore=15, spaceAfter=10)
    confidential_style = ParagraphStyle('Confidential', parent=styles['Normal'], fontSize=9, textColor=colors.red, alignment=1)
    body_style = styles['Normal']

    story.append(Paragraph("CONFIDENTIAL | STRATEGIC INTEL", confidential_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("STRATEGIC MEETING MINUTES", title_style))
    story.append(Paragraph(f"<b>Subject:</b> {title}", body_style))
    story.append(Paragraph(f"<b>Date:</b> {date}", body_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    story.append(Paragraph(summary, body_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("ACTION ITEMS & DELIVERABLES", heading_style))
    
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

# --- 3. PREMIUM UI/UX (Glass-Morphism Dark Theme) ---
st.set_page_config(page_title="Strategic Meeting Intelligence", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.75), rgba(0,0,0,0.75)), 
                    url("https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=2069");
        background-size: cover;
        background-attachment: fixed;
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.96);
        padding: 2.2rem;
        border-radius: 20px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.6);
        color: #0f172a;
        margin-bottom: 25px;
    }
    .main-title { color: white; font-size: 3.2rem; font-weight: 800; text-align: center; margin-bottom: 1rem; }
    .stButton>button {
        background-image: linear-gradient(to right, #1e40af, #1e3a8a);
        color: white; border-radius: 12px; font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>💼 Enterprise Hub</h2>", unsafe_allow_html=True)
    choice = st.sidebar.radio("Navigation", ["🚀 Intelligence Suite", "📅 Meeting Archives", "💬 Strategic Advisor"])
    st.markdown("---")
    st.caption("Strategic Meeting Intelligence v4.0")

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 Intelligence Suite":
    st.markdown("<h1 class='main-title'>Meeting Synthesis</h1>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    audio_file = st.file_uploader("Upload Meeting Audio/Video", type=["mp3", "wav", "mp4", "m4a"])
    m_title = st.text_input("Project / Meeting Title", placeholder="e.g. Q1 Operational Review")
    
    if audio_file and st.button("🚀 Process Intelligence"):
        with st.spinner("Synthesizing context and intent..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as tmp:
                tmp.write(audio_file.getvalue())
                tmp_path = tmp.name

            # Transcription
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Advanced Pattern Matching
            patterns = r"([^.]*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|will|must|deadline|by|due|schedule|complete|final|date)[^.]*\.)"
            actions = "\n".join([a.strip() for a in re.findall(patterns, raw_text, re.I)])

            # Summarization
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # Database Entry
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('meetings_pro.db')
            conn.execute("INSERT INTO meeting_history (date, title, summary, actions, transcript) VALUES (?,?,?,?,?)",
                         (ts, m_title, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.success("Analysis complete. Archive updated.")
            pdf_path = create_pro_pdf(m_title, summary, actions, ts)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download Branded MoM (PDF)", f, file_name=f"{m_title}.pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown("<h1 class='main-title'>Intelligence Records</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect('meetings_pro.db')
    data = conn.execute("SELECT * FROM meeting_history ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("Archives are currently empty.")
    else:
        for row in data:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([4, 1.5, 0.5])
            with col1:
                st.subheader(f"📌 {row[2]}")
                st.caption(f"Logged on: {row[1]}")
            with col2:
                if st.button("Edit Record", key=f"e_{row[0]}"):
                    st.session_state[f"ed_{row[0]}"] = not st.session_state.get(f"ed_{row[0]}", False)
            with col3:
                if st.button("🗑️", key=f"d_{row[0]}"):
                    delete_meeting(row[0])
                    st.rerun()

            if st.session_state.get(f"ed_{row[0]}", False):
                new_s = st.text_area("Summary", row[3], height=120, key=f"s_{row[0]}")
                new_a = st.text_area("Deliverables", row[4], height=120, key=f"a_{row[0]}")
                if st.button("Update Sync", key=f"up_{row[0]}"):
                    c = conn.cursor()
                    c.execute("UPDATE meeting_history SET summary=?, actions=? WHERE id=?", (new_s, new_a, row[0]))
                    conn.commit()
                    st.toast("Sync Successful!")
            st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- TAB 3: STRATEGIC ADVISOR (FIXED IndexError) ---
elif choice == "💬 Strategic Advisor":
    st.markdown("<h1 class='main-title'>Strategic Query Bot</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect('meetings_pro.db')
    # FIX: Corrected indexes for SELECT query
    rows = conn.execute("SELECT title, transcript FROM meeting_history").fetchall()
    recs = {r[0]: r[1] for r in rows} # r[0] is title, r[1] is transcript
    
    if recs:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        sel = st.selectbox("Select Context for Query", list(recs.keys()))
        query = st.text_input("Ask about specific decisions or mentions...")
        if query:
            ctx = recs[sel]
            # Advanced keyword context matching
            matches = [s for s in ctx.split('.') if any(w.lower() in s.lower() for w in query.split())]
            if matches:
                st.info(f"**Advisor Response:** {'. '.join(matches[:2])}.")
            else:
                st.warning("No direct mention found. Please use specific keywords like 'budget' or 'deadline'.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Please process a meeting first to enable the Strategic Advisor.")
    conn.close()
