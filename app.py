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
    # Schema includes 'type' for Corporate/Academic classification
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, type TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

def delete_record(record_id):
    conn = sqlite3.connect('strategic_intel_final.db')
    conn.execute("DELETE FROM archives WHERE id=?", (record_id,))
    conn.commit()
    conn.close()

# --- 2. STABLE EXECUTIVE PDF ENGINE ---
def generate_pro_pdf(title, summary, actions, date, m_type):
    pdf_path = f"Executive_MoM_{date.replace(':', '-')}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Premium Indigo & Blue Palette
    primary_blue = colors.Color(0.12, 0.16, 0.22) # #1E2A38
    accent_blue = colors.Color(0.31, 0.49, 1)    # #4F7CFF

    h1 = ParagraphStyle('H1', fontSize=22, textColor=primary_blue, spaceAfter=20, fontName="Helvetica-Bold")
    h2 = ParagraphStyle('H2', fontSize=14, textColor=accent_blue, spaceBefore=15, spaceAfter=10, fontName="Helvetica-Bold")
    body = ParagraphStyle('B', fontSize=10, leading=14, fontName="Helvetica")

    story.append(Paragraph("STRATEGIC MEETING INTELLIGENCE", h1))
    story.append(Paragraph(f"<b>REFERENCE:</b> {title.upper()} ({m_type})", body))
    story.append(Paragraph(f"<b>TIMESTAMP:</b> {date}", body))
    story.append(Spacer(1, 25))

    story.append(Paragraph("EXECUTIVE SUMMARY", h2))
    story.append(Paragraph(summary, body))
    story.append(Spacer(1, 20))

    story.append(Paragraph("ACTION ITEMS & DELIVERABLES", h2))
    table_data = [["REF", "DESCRIPTION / DEADLINE"]]
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

# --- 3. PREMIUM SaaS UI/UX (Slate & Glass Theme) ---
st.set_page_config(page_title="Strategic Meeting Intelligence", layout="wide", page_icon="💼")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC !important; }
    
    /* Sidebar Overrides */
    [data-testid="stSidebar"] { background-color: #0F172A !important; color: white !important; }
    
    /* Executive Glass Cards */
    .executive-card {
        background: white; padding: 2.5rem; border-radius: 16px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 2rem; color: #1E293B;
    }
    
    .main-title { color: #1E2A38; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
    .sub-title { color: #64748B; font-size: 16px; margin-bottom: 32px; }
    
    /* Badge Styles */
    .badge { padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .badge-corp { background: #E0E7FF; color: #4338CA; }
    .badge-edu { background: #DCFCE7; color: #15803D; }
    
    /* AI Chat Bubble */
    .ai-bubble {
        background-color: #F1F5F9; border-left: 5px solid #4F7CFF;
        padding: 1.5rem; border-radius: 12px; margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. WORKSPACE NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>💼 Workspace</h2>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", 
                          ["Corporate Meeting", "Academic Class", "Public Webinar", "Strategy Sync"])
    st.markdown("---")
    choice = st.radio("Navigation", ["🚀 Intelligence Suite", "📅 Meeting Archives", "💬 Strategic Advisor"], label_visibility="collapsed")
    st.caption(f"Context: {m_type}")

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 Intelligence Suite":
    st.markdown(f'<h1 class="main-title">{m_type} Analysis</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Synthesize recordings into structured strategic insights.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    
    if file:
        if file.type.startswith('video'):
            st.video(file) # Supports Google Meet/Zoom MP4s
        else:
            st.audio(file)
            
    title = st.text_input("Meeting Subject / Project Name", placeholder="e.g. Q1 Operational Review")
    
    if file and st.button("🚀 Process Intelligence"):
        with st.spinner("AI is decoding meeting context..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # AI Logic (Whisper natively extracts audio from video)
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Adaptive Intent Extraction
            patterns = r"([^.]*(?:monday|friday|deadline|will|must|homework|assignment|submit|due|by)[^.]*\.)"
            actions = "\n".join([f"• {a.strip()}" for a in re.findall(patterns, raw_text, re.I)])

            # Professional Summarization
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # Database Persistence
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel_final.db')
            conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                         (ts, title, m_type, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.success("Intelligence Synchronized!")
            pdf_out = generate_pro_pdf(title, summary, actions, ts, m_type)
            with open(pdf_out, "rb") as f:
                st.download_button("📥 Download Official MoM (PDF)", f, file_name=f"{title}.pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES (FIXED VIEW) ---
elif choice == "📅 Meeting Archives":
    st.markdown('<h1 class="main-title">Intelligence Archives</h1>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_final.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("Your processed meetings will appear here.")
    else:
        for row in data:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([4, 1.5, 0.5])
            with c1:
                badge_style = "badge-edu" if "Academic" in row[3] else "badge-corp"
                st.markdown(f"### {row[2]} <span class='badge {badge_style}'>{row[3]}</span>", unsafe_allow_html=True)
                st.caption(f"📅 {row[1]} • Synchronized")
            with c2:
                if st.button("Review/Edit", key=f"rev_{row[0]}"):
                    st.session_state[f"exp_{row[0]}"] = not st.session_state.get(f"exp_{row[0]}", False)
            with c3:
                if st.button("🗑️", key=f"del_{row[0]}"):
                    delete_record(row[0])
                    st.rerun() # Instant Refresh after delete
            
            if st.session_state.get(f"exp_{row[0]}", False):
                st.markdown("---")
                e_sum = st.text_area("Summary", row[4], height=120, key=f"es_{row[0]}")
                e_act = st.text_area("Actions", row[5], height=120, key=f"ea_{row[0]}")
                if st.button("Save Changes", key=f"sv_{row[0]}"):
                    c = conn.cursor()
                    c.execute("UPDATE archives SET summary=?, actions=? WHERE id=?", (e_sum, e_act, row[0]))
                    conn.commit()
                    st.toast("Updated Successfully!")
            st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- TAB 3: STRATEGIC ADVISOR (FIXED DROPDOWN & Q&A) ---
elif choice == "💬 Strategic Advisor":
    st.markdown('<h1 class="main-title">Strategic Advisor</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Query past session intelligence using natural language.</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('strategic_intel_final.db')
    rows = conn.execute("SELECT title, transcript FROM archives").fetchall()
    # Correct mapping for dropdown
    recs = {r[0]: r[1] for r in rows} 
    
    if recs:
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        # Dropdown fix: List of keys (titles) populate correctly
        sel_m = st.selectbox("Select Session Context", list(recs.keys()))
        query = st.text_input("Ask a question (e.g., What was the deadline discussed?)")
        
        if query:
            context = recs[sel_m]
            # Precise sentence retrieval
            matches = [s.strip() for s in context.split('.') if any(w.lower() in s.lower() for w in query.split())]
            
            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                st.write(f"**Advisor Response:** Based on '{sel_m}', I found: {'. '.join(matches[:2])}.")
            else:
                st.write("**Advisor Response:** No direct mention found. Try broader keywords like 'deadline' or 'task'.")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Archives are empty. Process a meeting to enable the Advisor.")
    conn.close()
