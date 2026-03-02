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

# --- 2. PROFESSIONAL PDF GENERATOR ---
def create_pro_pdf(title, summary, actions, date):
    pdf_path = f"MoM_{date.replace(':', '-')}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.hexColor("#0f172a"), spaceAfter=10)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.hexColor("#2563eb"), spaceBefore=15, spaceAfter=8)
    body_style = styles['Normal']

    story.append(Paragraph("STRATEGIC MEETING MINUTES", title_style))
    story.append(Paragraph(f"<b>Subject:</b> {title}", body_style))
    story.append(Paragraph(f"<b>Date:</b> {date}", body_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    story.append(Paragraph(summary, body_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("ACTION ITEMS & DELIVERABLES", heading_style))
    action_data = [["ID", "Description"]]
    for i, item in enumerate(actions.split('\n'), 1):
        if item.strip():
            action_data.append([str(i), item.strip()])

    if len(action_data) > 1:
        t = Table(action_data, colWidths=[40, 440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.hexColor("#f8fafc")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.hexColor("#1e293b")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No specific action items identified.", body_style))
    
    doc.build(story)
    return pdf_path

init_db()

# --- 3. UI/UX CONFIG (Clean & Modern) ---
st.set_page_config(page_title="Pro Meeting Intel", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    .main-title { color: #0f172a; font-size: 2.2rem; font-weight: 800; }
    .card {
        background: white; padding: 1.5rem; border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); margin-bottom: 1rem;
    }
    .delete-btn { color: #ef4444 !important; border-color: #ef4444 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.title("💼 Workspace")
    choice = st.radio("Menu", ["🚀 New Analysis", "📅 Meeting Archives", "💬 AI Consultant"])

# --- TAB 1: NEW ANALYSIS ---
if choice == "🚀 New Analysis":
    st.markdown("<h1 class='main-title'>Strategic Synthesis</h1>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        audio_file = st.file_uploader("Upload Meeting Audio/Video", type=["mp3", "wav", "mp4", "m4a"])
        m_title = st.text_input("Meeting Subject", placeholder="e.g. Council Budget Review")
        
        if audio_file and st.button("Generate Intelligence"):
            with st.spinner("AI is decoding meeting context..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as tmp:
                    tmp.write(audio_file.getvalue())
                    tmp_path = tmp.name

                w_model = whisper.load_model("base")
                result = w_model.transcribe(tmp_path)
                raw_text = result["text"]
                os.remove(tmp_path)

                # Intent Analysis (Dates & Keywords)
                p = r"([^.]*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|will|must|deadline|by|due|schedule|complete)[^.]*\.)"
                actions = "\n".join([a.strip() for a in re.findall(p, raw_text, re.I)])

                # Summarization
                tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
                s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
                inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
                sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
                summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

                # Save Data
                ts = datetime.now().strftime("%d-%m-%Y %H:%M")
                conn = sqlite3.connect('meetings_pro.db')
                conn.execute("INSERT INTO meeting_history (date, title, summary, actions, transcript) VALUES (?,?,?,?,?)",
                             (ts, m_title, summary, actions, raw_text))
                conn.commit()
                conn.close()

                st.success("Successfully processed!")
                pdf = create_pro_pdf(m_title, summary, actions, ts)
                with open(pdf, "rb") as f:
                    st.download_button("📥 Download Official Minutes", f, file_name=f"{m_title}.pdf")
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES (View & Delete) ---
elif choice == "📅 Meeting Archives":
    st.markdown("<h1 class='main-title'>Meeting Repository</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect('meetings_pro.db')
    data = conn.execute("SELECT * FROM meeting_history ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("No meetings found. Start by analyzing a new recording.")
    else:
        for row in data:
            with st.container():
                st.markdown(f'<div class="card">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([4, 2, 1])
                with col1:
                    st.markdown(f"**{row[2]}**")
                    st.caption(f"📅 {row[1]}")
                with col2:
                    if st.button("View/Edit", key=f"view_{row[0]}"):
                        st.session_state[f"edit_{row[0]}"] = not st.session_state.get(f"edit_{row[0]}", False)
                with col3:
                    if st.button("🗑️", key=f"del_{row[0]}"):
                        delete_meeting(row[0])
                        st.rerun()

                # Expandable Edit Section
                if st.session_state.get(f"edit_{row[0]}", False):
                    new_sum = st.text_area("Summary", row[3], height=100, key=f"ts_{row[0]}")
                    new_act = st.text_area("Actions", row[4], height=100, key=f"ta_{row[0]}")
                    if st.button("Save Changes", key=f"save_{row[0]}"):
                        c = conn.cursor()
                        c.execute("UPDATE meeting_history SET summary=?, actions=? WHERE id=?", (new_sum, new_act, row[0]))
                        conn.commit()
                        st.toast("Record Updated!")
                st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- TAB 3: AI CONSULTANT ---
elif choice == "💬 AI Consultant":
    st.markdown("<h1 class='main-title'>Strategic Query Bot</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect('meetings_pro.db')
    recs = {r[2]: r[5] for r in conn.execute("SELECT title, transcript FROM meeting_history").fetchall()}
    
    if recs:
        sel = st.selectbox("Select Meeting Context", list(recs.keys()))
        q = st.text_input("Ask about this meeting (e.g. Budget decisions?)")
        if q:
            ctx = recs[sel]
            ans = [s for s in ctx.split('.') if any(w.lower() in s.lower() for w in q.split())]
            st.info(f"**AI:** {'. '.join(ans[:2]) if ans else 'No specific info found.'}")
    else:
        st.info("Archives are empty.")
    conn.close()
