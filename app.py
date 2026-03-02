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

# --- 1. DATABASE ARCHITECTURE ---
def init_db():
    conn = sqlite3.connect('strategic_intel_master.db')
    c = conn.cursor()
    # Supports meeting types for categorized archives
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, type TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

def delete_meeting(m_id):
    conn = sqlite3.connect('strategic_intel_master.db')
    conn.execute("DELETE FROM archives WHERE id=?", (m_id,))
    conn.commit()
    conn.close()

# --- 2. PROFESSIONAL PDF GENERATOR (MoM) ---
def create_pdf(title, summary, actions, date, m_type):
    pdf_path = f"Report_{date.replace(':', '-')}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Enterprise Color Palette
    p_blue = colors.Color(30/255, 42/255, 56/255) # #1E2A38
    a_blue = colors.Color(79/255, 124/255, 255/255) # #4F7CFF

    title_s = ParagraphStyle('T', fontSize=22, textColor=p_blue, spaceAfter=20, fontName="Helvetica-Bold")
    sub_s = ParagraphStyle('S', fontSize=14, textColor=a_blue, spaceBefore=15, spaceAfter=10, fontName="Helvetica-Bold")
    body_s = ParagraphStyle('B', fontSize=10, leading=14, fontName="Helvetica")

    story.append(Paragraph("STRATEGIC MEETING INTELLIGENCE", title_s))
    story.append(Paragraph(f"<b>SESSION:</b> {title.upper()} | <b>TYPE:</b> {m_type}", body_s))
    story.append(Paragraph(f"<b>DATE:</b> {date}", body_s))
    story.append(Spacer(1, 25))

    story.append(Paragraph("EXECUTIVE SUMMARY", sub_s))
    story.append(Paragraph(summary, body_s))
    story.append(Spacer(1, 20))

    story.append(Paragraph("KEY ASSIGNMENTS & DELIVERABLES", sub_s))
    table_data = [["ID", "TASK / ACCOUNTABILITY"]]
    for i, item in enumerate(actions.split('\n'), 1):
        if item.strip():
            table_data.append([str(i), item.strip().replace('• ', '')])

    if len(table_data) > 1:
        t = Table(table_data, colWidths=[40, 440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.Color(0.95, 0.97, 0.98)),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
    
    doc.build(story)
    return pdf_path

init_db()

# --- 3. PREMIUM SaaS UI/UX ---
st.set_page_config(page_title="Strategic Intel", layout="wide", page_icon="💼")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC !important; }
    
    /* Executive Cards */
    .executive-card {
        background: white; padding: 2rem; border-radius: 12px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem; color: #1E293B;
    }
    .main-title { color: #1E2A38; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
    .sub-title { color: #64748B; font-size: 16px; margin-bottom: 30px; }
    
    /* Workspace Badges */
    .badge { padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .badge-corp { background: #E0E7FF; color: #4338CA; }
    .badge-edu { background: #DCFCE7; color: #15803D; }

    /* AI Bubble */
    .ai-bubble { background-color: #F1F5F9; border-left: 5px solid #4F7CFF; padding: 1.2rem; border-radius: 10px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION & SETTINGS ---
with st.sidebar:
    st.markdown("<h2 style='color:#1E2A38;'>💼 Workspace</h2>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", 
                          ["Corporate Board Sync", "Academic Lecture/Class", "Strategic Webinar", "Technical Sprint"])
    st.markdown("---")
    choice = st.radio("Menu", ["🚀 Intelligence Suite", "📅 Records Archive", "💬 Strategic Advisor"], label_visibility="collapsed")

# --- TAB 1: INTELLIGENCE SUITE (Processing) ---
if choice == "🚀 Intelligence Suite":
    st.markdown(f'<h1 class="main-title">{m_type} Analysis</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Upload recordings to extract high-value intelligence.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Video or Audio", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    
    if file:
        if file.type.startswith('video'):
            st.video(file) # Video Preview Feature
        else:
            st.audio(file)
            
    title = st.text_input("Session Reference", placeholder="e.g. Q1 Marketing Sync or Physics Lecture 10")
    
    if file and st.button("🚀 Process Intelligence"):
        with st.spinner("AI is synthesizing meeting context..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # AI Logic: Whisper extracts audio from video natively
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Assignment Logic: Detect "Who to Whom"
            patterns = r"([^.]*(?:will|must|deadline|homework|assignment|submit|due|tasked)[^.]*\.)"
            actions = "\n".join([f"• {a.strip()}" for a in re.findall(patterns, raw_text, re.I)])

            # Summarization Engine
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # Persistent Sync
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel_master.db')
            conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                         (ts, title, m_type, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.success("Intelligence Synchronized!")
            pdf_out = create_pdf(title, summary, actions, ts, m_type)
            with open(pdf_out, "rb") as f:
                st.download_button("📥 Download Official MoM", f, file_name=f"{title}.pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: RECORDS ARCHIVE (Fixed View) ---
elif choice == "📅 Records Archive":
    st.markdown('<h1 class="main-title">Intelligence Archives</h1>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_master.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("Archives are currently empty. Process a session to view records.")
    else:
        for row in data:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([4, 1.5, 0.5])
            with c1:
                b_class = "badge-edu" if "Academic" in str(row[3]) else "badge-corp"
                st.markdown(f"### {row[2]} <span class='badge {b_class}'>{row[3]}</span>", unsafe_allow_html=True)
                st.caption(f"📅 Recorded: {row[1]}")
            with c2:
                if st.button("Review Details", key=f"v_{row[0]}"):
                    st.session_state[f"sh_{row[0]}"] = not st.session_state.get(f"sh_{row[0]}", False)
            with c3:
                if st.button("🗑️", key=f"d_{row[0]}"):
                    delete_meeting(row[0])
                    st.rerun()
            
            if st.session_state.get(f"sh_{row[0]}", False):
                st.markdown("---")
                st.markdown(f"**Summary:** {row[4]}")
                st.markdown(f"**Action Items:** {row[5]}")
            st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- TAB 3: STRATEGIC ADVISOR (Fixed Mapping & Q&A) ---
elif choice == "💬 Strategic Advisor":
    st.markdown('<h1 class="main-title">Strategic Advisor</h1>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_master.db')
    rows = conn.execute("SELECT title, transcript FROM archives").fetchall()
    # Correct mapping for dropdown
    recs = {r[0]: r[1] for r in rows} 
    
    if recs:
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        # Dropdown fix: List of keys (titles) populate correctly
        sel_m = st.selectbox("Choose Session Context", list(recs.keys()))
        query = st.text_input("Consult with AI about this session...", placeholder="e.g. What was Rahul's role?")
        
        if query:
            context = recs[sel_m]
            # Pinpoint sentence retrieval
            sentences = context.split('.')
            matches = [s.strip() for s in sentences if any(w.lower() in s.lower() for w in query.split())]
            
            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                st.write(f"**Advisor Response:** Based on '{sel_m}', I found: {'. '.join(matches[:2])}.")
            else:
                st.write("**Advisor Response:** No direct mention found. Try broader keywords like 'task' or 'deadline'.")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Process a meeting to enable the Strategic Advisor.")
    conn.close()
