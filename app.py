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
    conn = sqlite3.connect('strategic_intel_v8.db')
    c = conn.cursor()
    # Schema supports meeting types for categorized archives
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, type TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

def delete_record(record_id):
    conn = sqlite3.connect('strategic_intel_v8.db')
    conn.execute("DELETE FROM archives WHERE id=?", (record_id,))
    conn.commit()
    conn.close()

# --- 2. STABLE PDF ENGINE ---
def generate_pro_pdf(title, summary, actions, date, m_type):
    pdf_path = f"Executive_Report_{date.replace(':', '-')}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    p_blue = colors.Color(0.12, 0.16, 0.22) 
    a_blue = colors.Color(0.31, 0.49, 1)    

    h1 = ParagraphStyle('H1', fontSize=22, textColor=p_blue, spaceAfter=20, fontName="Helvetica-Bold")
    h2 = ParagraphStyle('H2', fontSize=14, textColor=a_blue, spaceBefore=15, spaceAfter=10, fontName="Helvetica-Bold")
    body = ParagraphStyle('B', fontSize=10, leading=14, fontName="Helvetica")

    story.append(Paragraph("STRATEGIC MEETING INTELLIGENCE", h1))
    story.append(Paragraph(f"<b>REFERENCE:</b> {title.upper()} ({m_type})", body))
    story.append(Paragraph(f"<b>TIMESTAMP:</b> {date}", body))
    story.append(Spacer(1, 25))

    story.append(Paragraph("EXECUTIVE SUMMARY", h2))
    story.append(Paragraph(summary, body))
    story.append(Spacer(1, 20))

    story.append(Paragraph("ACTIONABLE DELIVERABLES", h2))
    table_data = [["REF", "TASK / DEADLINE"]]
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

# --- 3. PREMIUM SaaS UI/UX CONFIG ---
st.set_page_config(page_title="Strategic Intel | AI Meeting Assistant", layout="wide", page_icon="💼")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; color: white !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: white !important; }
    
    .hero-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 3rem 2rem; border-radius: 16px; margin-bottom: 2.5rem; color: white;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1); text-align: center;
    }
    .hero-banner h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; letter-spacing: -0.02em; }
    .hero-banner p { font-size: 1.1rem; color: #94a3b8; font-weight: 300; }
    
    .executive-card {
        background: white; padding: 2rem; border-radius: 12px; border: 1px solid #E2E8F0; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1.5rem; 
    }
    .ai-bubble {
        background-color: #F1F5F9; border-left: 4px solid #3b82f6; padding: 1.25rem; 
        border-radius: 0 12px 12px 0; margin: 1rem 0; color: #334155;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>STRATEGIC INTEL</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#334155'>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Strategy Sync"])
    choice = st.radio("Navigation", ["🚀 Intelligence Suite", "📅 Meeting Archives"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("v8.0 Enterprise Edition")

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 Intelligence Suite":
    st.markdown("""
    <div class="hero-banner">
        <h1>Missed a meeting? No need to rewatch it.</h1>
        <p>Upload your recording. We'll extract the insights, generate the summary, and answer your questions instantly.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    title = st.text_input("Session Title", placeholder="e.g., Q1 Product Sync")
    
    if file:
        if file.type.startswith('video'): st.video(file)
        else: st.audio(file)
                
    if st.button("🚀 Process Intelligence", type="primary", use_container_width=True):
        with st.spinner("Analyzing context..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            st.session_state['current_transcript'] = raw_text
            p = r"([^.]*(?:monday|friday|deadline|will|must|homework|assignment|submit|due|by|tasked|decided)[^.]*\.)"
            actions = "\n".join([f"• {a.strip()}" for a in re.findall(p, raw_text, re.I)])

            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
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
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if 'summary' in st.session_state:
        st.divider()
        st.subheader("Executive Synthesis")
        c1, c2 = st.columns(2)
        with c1: st.info(f"**📚 Summary:**\n\n{st.session_state['summary']}")
        with c2: st.success(f"**🎯 Action Items:**\n\n{st.session_state['actions']}")

        pdf_file = generate_pro_pdf(title, st.session_state['summary'], st.session_state['actions'], st.session_state['ts'], m_type)
        with open(pdf_file, "rb") as f:
            st.download_button("📥 Download Official Report (PDF)", f, file_name=f"{title}_Report.pdf")

        st.divider()
        st.subheader("💬 Strategic Query Engine")
        user_q = st.text_input("Ask about Rahul's role, deadlines, or specific decisions...")
        if user_q:
            ctx = st.session_state['current_transcript']
            sentences = [s.strip() for s in ctx.split('.') if len(s.strip()) > 5]
            query_words = [w.lower() for w in user_q.split() if len(w) > 3]
            matches = [s for s in sentences if any(w in s.lower() for w in query_words)]

            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                st.write(f"**Advisor Response:** Based on the transcript: *{'. '.join(matches[:2])}*")
            else:
                st.write("**Advisor Response:** Context found, but no specific mention of those terms.")
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown('<div class="hero-banner" style="padding: 1.5rem;"><h1>Archives</h1></div>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_v8.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    if not data: st.info("No records found.")
    else:
        for row in data:
            with st.expander(f"📅 {row[1]} | {row[2]} ({row[3]})"):
                st.markdown(f"**Summary:** {row[4]}")
                st.markdown(f"**Action Items:** {row[5]}")
                if st.button("Delete", key=f"d_{row[0]}"): 
                    delete_record(row[0])
                    st.rerun()
    conn.close()
