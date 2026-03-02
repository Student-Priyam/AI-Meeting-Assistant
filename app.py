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

# --- 1. GLOBAL UI & UX CONFIGURATION (Premium SaaS Style) ---
st.set_page_config(
    page_title="Strategic Meeting Intelligence",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the "Executive Slate" Design System
st.markdown("""
    <style>
    /* Import Enterprise Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #F5F7FA !important;
    }

    /* Fixed Left Sidebar (240px) */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E6EAF0;
        min-width: 240px !important;
    }

    /* Sidebar Active State Styling */
    .st-emotion-cache-16idsys p {
        font-weight: 500;
        color: #1E2A38;
    }

    /* Executive Card Styling */
    .executive-card {
        background: white;
        padding: 2.5rem;
        border-radius: 12px;
        border: 1px solid #E6EAF0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        margin-bottom: 2rem;
    }

    /* Typography Hierarchy */
    .page-title { color: #1E2A38; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
    .page-subtitle { color: #64748B; font-size: 16px; margin-bottom: 32px; }

    /* Buttons: Electric Blue Accent */
    .stButton>button {
        background-color: #4F7CFF !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        transition: 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #3D62D6 !important;
        box-shadow: 0 4px 12px rgba(79, 124, 255, 0.3);
    }

    /* Status Badge: Success Green */
    .badge-processed {
        background-color: #ECFDF5;
        color: #059669;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE SYSTEM LOGIC ---
def init_db():
    conn = sqlite3.connect('strategic_intel.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

# FIX: Stable PDF Generation (Resolved AttributeError)
def generate_pdf(title, summary, actions, date):
    pdf_path = f"MoM_{date.replace(':', '-')}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Using Hex colors safely via direct assignment
    primary_color = colors.Color(red=(30/255), green=(42/255), blue=(56/255)) # #1E2A38
    accent_color = colors.Color(red=(79/255), green=(124/255), blue=(255/255)) # #4F7CFF

    h1_style = ParagraphStyle('H1', fontSize=22, textColor=primary_color, spaceAfter=20, fontName="Helvetica-Bold")
    h2_style = ParagraphStyle('H2', fontSize=14, textColor=accent_color, spaceBefore=15, spaceAfter=10, fontName="Helvetica-Bold")
    body_style = ParagraphStyle('B', fontSize=10, leading=14, fontName="Helvetica")

    story.append(Paragraph("STRATEGIC MEETING INTELLIGENCE", h1_style))
    story.append(Paragraph(f"<b>REFERENCE:</b> {title.upper()}", body_style))
    story.append(Paragraph(f"<b>TIMESTAMP:</b> {date}", body_style))
    story.append(Spacer(1, 24))

    story.append(Paragraph("EXECUTIVE SUMMARY", h2_style))
    story.append(Paragraph(summary, body_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("ACTION ITEMS & DELIVERABLES", h2_style))
    
    table_data = [["REF", "DESCRIPTION / DEADLINE"]]
    for i, item in enumerate(actions.split('\n'), 1):
        if item.strip():
            table_data.append([str(i), item.strip()])

    if len(table_data) > 1:
        t = Table(table_data, colWidths=[40, 440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.Color(0.96, 0.97, 0.98)),
            ('TEXTCOLOR', (0,0), (-1,0), primary_color),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
    
    doc.build(story)
    return pdf_path

init_db()

# --- 3. WORKSPACE NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:#1E2A38; margin-top:0;'>💼 Workspace</h2>", unsafe_allow_html=True)
    mode = st.radio("Navigation", ["🚀 Intelligence Suite", "📅 Meeting Archives", "💬 Strategic Advisor"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("Strategic Intel v5.0 • Enterprise Edition")

# --- 4. PAGE 1: INTELLIGENCE SUITE ---
if mode == "🚀 Intelligence Suite":
    st.markdown('<h1 class="page-title">Turn Meetings Into Strategic Insights</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Upload your meeting and generate structured summaries instantly.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Meeting Audio/Video", type=["mp3", "wav", "mp4", "m4a"], label_visibility="collapsed")
    title = st.text_input("Meeting Subject / Project Name", placeholder="e.g. Q1 Operations Review")
    
    if file and st.button("🚀 Process Intelligence"):
        with st.spinner("AI is synthesizing strategic intent..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # Transcription & AI Logic
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            patterns = r"([^.]*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|will|must|deadline|by|due|schedule|complete|final)[^.]*\.)"
            actions = "\n".join([a.strip() for a in re.findall(patterns, raw_text, re.I)])

            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # DB Save
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel.db')
            conn.execute("INSERT INTO archives (date, title, summary, actions, transcript) VALUES (?,?,?,?,?)",
                         (ts, title, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.toast("✅ Meeting Intelligence Synchronized")
            
            # Show Result in Clean Tabs
            t1, t2, t3 = st.tabs(["📄 Summary", "🎯 Action Items", "📥 Export"])
            with t1: st.markdown(f'<div class="ai-bubble">{summary}</div>', unsafe_allow_html=True)
            with t2: st.markdown(f'<div class="ai-bubble">{actions if actions else "No specific actions found."}</div>', unsafe_allow_html=True)
            with t3:
                pdf_out = generate_pdf(title, summary, actions, ts)
                with open(pdf_out, "rb") as f:
                    st.download_button("Download PDF", f, file_name=f"{title}_MoM.pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. PAGE 2: ARCHIVE CENTER ---
elif mode == "📅 Meeting Archives":
    st.markdown('<h1 class="page-title">Meeting Archives</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Your processed meetings with structured historical data.</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('strategic_intel.db')
    data = conn.execute("SELECT id, date, title, summary, actions FROM archives ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("Your processed meetings will appear here.")
    else:
        for row in data:
            with st.container():
                st.markdown('<div class="executive-card">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([4, 1.5, 0.5])
                with col1:
                    st.markdown(f"**{row[2]}**")
                    st.caption(f"📅 {row[1]} • <span class='badge-processed'>Processed</span>", unsafe_allow_html=True)
                with col2:
                    if st.button("Review", key=f"r_{row[0]}"):
                        st.session_state[f"exp_{row[0]}"] = not st.session_state.get(f"exp_{row[0]}", False)
                with col3:
                    if st.button("🗑️", key=f"d_{row[0]}"):
                        conn.execute("DELETE FROM archives WHERE id=?", (row[0],))
                        conn.commit()
                        st.rerun()
                
                if st.session_state.get(f"exp_{row[0]}", False):
                    st.markdown(f"**AI Summary:** {row[3]}")
                    st.markdown(f"**Actions:** {row[4]}")
                st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- 6. PAGE 3: STRATEGIC ADVISOR (Chat Bot) ---
elif mode == "💬 Strategic Advisor":
    st.markdown('<h1 class="page-title">Strategic Advisor</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Query past meeting intelligence using natural language.</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('strategic_intel.db')
    rows = conn.execute("SELECT title, transcript FROM archives").fetchall()
    recs = {r[0]: r[1] for r in rows}
    
    if recs:
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        sel = st.selectbox("Choose Meeting Context", list(recs.keys()))
        query = st.text_input("Consult with AI about this meeting...", placeholder="e.g. What was the decision on the budget?")
        
        if query:
            ctx = recs[sel]
            matches = [s for s in ctx.split('.') if any(w.lower() in s.lower() for w in query.split())]
            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                st.write(f"**Advisor Response:** Based on the transcript, {'. '.join(matches[:2])}.")
            else:
                st.write("**Advisor Response:** I could not find a specific mention of that topic in this meeting.")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Process a meeting recording first to enable the Advisor.")
    conn.close()
