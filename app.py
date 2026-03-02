<think>
The user wants the complete, updated code with the improved UI/UX I mentioned in my previous response. I will paste the full code block.
</think>, PDF, DB) but wrapped it in a much more professional "SaaS" interface with the banner you requested.

```python
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

# Custom CSS for Inter font, Sidebar, and Banner
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
    /* Main Font */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Background & Layout */
    .stApp { background-color: #F8FAFC; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] { 
        background-color: #0F172A !important; 
        color: white !important; 
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    /* Custom Banner */
    .hero-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 3rem 2rem;
        border-radius: 16px;
        margin-bottom: 2.5rem;
        color: white;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .hero-banner h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; letter-spacing: -0.02em; }
    .hero-banner p { font-size: 1.1rem; color: #94a3b8; font-weight: 300; }
    
    /* Cards */
    .executive-card {
        background: white; 
        padding: 2rem; 
        border-radius: 12px;
        border: 1px solid #E2E8F0; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem; 
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #cbd5e1;
        padding: 10px;
    }
    
    /* AI Response Bubble */
    .ai-bubble {
        background-color: #F1F5F9; 
        border-left: 4px solid #3b82f6;
        padding: 1.25rem; 
        border-radius: 0 12px 12px 0; 
        margin: 1rem 0;
        color: #334155;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button {
        gap: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION & BANNER ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center; letter-spacing:1px;'>STRATEGIC INTEL</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#334155'>", unsafe_allow_html=True)
    
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Strategy Sync"])
    st.markdown("---")
    choice = st.radio("Navigation", ["🚀 Intelligence Suite", "📅 Meeting Archives"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("""
    <div style="font-size:12px; color:#94a3b8; text-align:center;">
        <b>v8.0 Enterprise</b><br>Powered by Whisper & BART
    </div>
    """, unsafe_allow_html=True)

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 Intelligence Suite":
    
    # Hero Banner Section
    st.markdown("""
    <div class="hero-banner">
        <h1>Missed a meeting? No need to rewatch it.</h1>
        <p>Upload your audio or video. We'll extract the insights, generate the summary, and answer your questions instantly.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'### {m_type} Suite', unsafe_allow_html=True)
    
    # Input Area
    col_main, col_side = st.columns([3, 1])
    
    with col_main:
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        
        file = st.file_uploader("Upload Audio or Video File", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed", help="Supports MP3, WAV, MP4, MOV")
        title = st.text_input("Session Reference / Title", placeholder="e.g., Q3 Financial Review - Rahul's Team")
        
        if file:
            st.caption(f"📄 File loaded: {file.name}")
            if file.type.startswith('video'): 
                st.video(file) 
            else: 
                st.audio(file)
                
        process_btn = st.button("🚀 Process Intelligence", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Processing Logic
    if process_btn and file and title:
        with st.spinner("🤖 AI is decoding meeting context and strategic intent..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # 1. Transcription
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Store for Query
            st.session_state['current_transcript'] = raw_text

            # 2. Intent Extraction
            patterns = r"([^.]*(?:monday|friday|deadline|will|must|homework|assignment|submit|due|by|tasked|decided)[^.]*\.)"
            actions = "\n".join([f"• {a.strip()}" for a in re.findall(patterns, raw_text, re.I)])

            # 3. Summarization
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # 4. Save to DB
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

    # --- RESULTS & QUERY ---
    if 'summary' in st.session_state and 'actions' in st.session_state:
        st.divider()
        
        # Top Metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Session Date", st.session_state['ts'])
        with m2:
            st.metric("Action Items Detected", len(st.session_state['actions'].split('•'))-1)
        with m3:
            st.metric("Transcript Length", f"{len(st.session_state['current_transcript'])} chars")

        # Executive Output
        st.subheader("Executive Synthesis")
        c1, c2 = st.columns(2)
        
        # Summary Card
        with c1:
            st.info(f"**📚 Summary:**\n\n{st.session_state['summary']}")
        
        # Actions Card
        with c2:
            st.success(f"**🎯 { 'Assignments' if 'Academic' in m_type else 'Action Items' }:**\n\n{st.session_state['actions']}")

        # PDF Download
        pdf_file = generate_pro_pdf(title, st.session_state['summary'], st.session_state['actions'], st.session_state['ts'], m_type)
        with open(pdf_file, "rb") as f:
            st.download_button("📥 Download Official Report (PDF)", f, file_name=f"{title.replace(' ', '_')}_Report.pdf", type="secondary")

        # --- PINPOINT QUERY ---
        st.divider()
        st.subheader("💬 Strategic Query Engine")
        
        col_q1, col_q2 = st.columns([4,1])
        with col_q1:
            user_q = st.text_input("Ask about Rahul's role, deadlines, or specific decisions...", key="live_q")
        with col_q2:
            st.write("")
            st.write("")
            ask_btn = st.button("Ask AI", type="secondary")
        
        if user_q and ask_btn:
            ctx = st.session_state['current_transcript']
            sentences = [s.strip() for s in ctx.split('.') if len(s.strip()) > 5]
            query_words = [w.lower() for w in user_q.split() if len(w) > 3]
            matches = [s for s in sentences if any(w in s.lower() for w in query_words)]

            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                st.write(f"**Advisor Response:** Based on the transcript: *{'. '.join(matches[:2])}*")
            else:
                st.write("**Advisor Response:** I found the meeting context, but no specific mention of those terms.")
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown("""
    <div class="hero-banner" style="padding: 1.5rem;">
        <h1>Intelligence Archives</h1>
        <p>Review historical meeting intelligence.</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = sqlite3.connect('strategic_intel_v8.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    
    if not data: 
        st.info("No processed records found. Go to the Intelligence Suite to process a meeting.")
    else:
        for row in data:
            with st.expander(f"📅 {row[1]} | {row[2]} ({row[3]})"):
                c1, c2 = st.columns([6, 1])
                with c1: 
                    st.markdown(f"**Summary:** {row[4]}")
                    st.markdown(f"**Action Items:** {row[5]}")
                with c2:
                    if st.button("Delete", key=f"d_{row[0]}"): 
                        delete_record(row[0]) 
                        st.rerun()
    conn.close()
```
