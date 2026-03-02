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
    
    # Premium Palette
    p_blue = colors.Color(0.12, 0.16, 0.22) # #1E2A38
    a_blue = colors.Color(0.31, 0.49, 1)    # #4F7CFF

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

# Custom CSS with integrated natural banner and circled text fixes
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
    
    /* UPDATED Natural Banner Image - Fixed CIRCLED TEXT and IMAGE */
    .hero-banner {
        background-image: linear-gradient(rgba(15, 23, 42, 0.8), rgba(15, 23, 42, 0.8)), 
                          url('https://images.unsplash.com/photo-1517048676732-d65bc937f952?q=80&w=2070');
        background-size: cover;
        background-position: center;
        padding: 5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2.5rem;
        color: white;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        text-align: center;
        position: relative;
    }
    .hero-banner h1 { font-size: 2.8rem; font-weight: 700; margin-bottom: 0.5rem; letter-spacing: -0.02em; text-shadow: 0px 2px 4px rgba(0,0,0,0.5); }
    .hero-banner p { font-size: 1.2rem; color: #E0E7FF; font-weight: 300; text-shadow: 0px 1px 2px rgba(0,0,0,0.5); }
    
    /* Executive Card */
    .executive-card {
        background: white; 
        padding: 2.5rem; 
        border-radius: 12px;
        border: 1px solid #E2E8F0; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem; 
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #cbd5e1;
        padding: 12px;
    }
    
    /* AI Response Bubble */
    .ai-bubble {
        background-color: #F1F5F9; 
        border-left: 4px solid #3b82f6;
        padding: 1.5rem; 
        border-radius: 0 12px 12px 0; 
        margin: 1rem 0;
        color: #334155;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button {
        gap: 1.5rem;
        font-weight: 600;
    }
    
    /* Badge for Academic/Corporate type */
    .badge-academic { background-color: #FEF3C7; color: #92400E; padding: 4px 8px; border-radius: 9999px; font-weight: 600; font-size: 0.75rem; }
    .badge-corporate { background-color: #DBEAFE; color: #1E40AF; padding: 4px 8px; border-radius: 9999px; font-weight: 600; font-size: 0.75rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center; letter-spacing:1px; font-weight:700;'>STRATEGIC INTEL</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#334155'>", unsafe_allow_html=True)
    
    m_type = st.selectbox("Meeting Type", ["Corporate Sync", "Academic Lecture", "Webinar Q&A", "Technical Sprint"])
    st.markdown("---")
    choice = st.radio("Navigation", ["🚀 New Intelligence", "📅 Historical Archives"], label_visibility="collapsed")
    
    # CIRCLED TEXT REMOVED
    st.markdown("---")
    # Clean footer
    st.markdown("""
    <div style="font-size:12px; color:#94a3b8; text-align:center;">
        v8.0 Professional Edition<br>
        Powered by OpenAI Whisper & BART
    </div>
    """, unsafe_allow_html=True)

# --- TAB 1: INTELLIGENCE SUITE ---
if choice == "🚀 New Intelligence":
    
    # Hero Banner Section - Integrates natural meeting image and bold text
    st.markdown("""
    <div class="hero-banner">
        <h1>Missed a meeting?</h1>
        <h1>Get instantly up to speed.</h1>
        <p>Upload your session recording. Our AI extracts core insights, summarizes decisions,<br>and answers specific questions in seconds.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<h3 style="color:#1E2A38; font-weight:700; margin-top:2rem;">{m_type} Suite</h3>', unsafe_allow_html=True)
    
    # Input Area
    col_main, col_side = st.columns([3, 1])
    
    with col_main:
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        
        file = st.file_uploader("Upload Audio or Video File", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed", help="Supports MP3, WAV, MP4, MOV. Max size ~200MB.")
        title = st.text_input("Session Title (e.g., Project Atlas Roadmap)", placeholder="Sprint 24 Planning - Mobile Team")
        
        if file:
            st.caption(f"✅ Ready to process: **{file.name}**")
            with col_side:
                # Video Preview in side column for balanced layout
                if file.type.startswith('video'): 
                    st.video(file) # Full video support
                else: 
                    st.audio(file)
                
        process_btn = st.button("🚀 Process New Intelligence", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Processing Logic
    if process_btn and file and title:
        with st.spinner("🤖 AI is decoding session context, tracking assignments, and preparing your summary..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # 1. Transcription - Whisper natively extracts audio from video
            try:
                w_model = whisper.load_model("base")
                result = w_model.transcribe(tmp_path)
                raw_text = result["text"]
            except Exception as e:
                st.error(f"Error during transcription: {e}")
                st.stop()
            finally:
                os.remove(tmp_path)

            # Store full text for Query
            st.session_state['current_transcript'] = raw_text

            # 2. Intent Extraction - Detect assignments and deadlines
            p = r"([^.]*(?:monday|friday|deadline|will|must|homework|assignment|submit|due|by|tasked|decided)[^.]*\.)"
            actions = "\n".join([f"• {a.strip()}" for a in re.findall(patterns, raw_text, re.I)])

            # 3. Summarization - Use BART optimized for minutes
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # 4. Save to DB
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            try:
                conn = sqlite3.connect('strategic_intel_v8.db')
                conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                             (ts, title, m_type, summary, actions, raw_text))
                conn.commit()
            except sqlite3.Error as e:
                st.error(f"Database error: {e}")
            finally:
                conn.close()

            # Store outputs in session state
            st.session_state['current_analysis_title'] = title
            st.session_state['summary'] = summary
            st.session_state['actions'] = actions
            st.session_state['ts'] = ts
            
            st.rerun()

    # --- RESULTS & SMART QUERY ---
    if 'summary' in st.session_state and 'actions' in st.session_state:
        st.divider()
        
        # Header with badge
        badge_class = "badge-academic" if "Academic" in m_type else "badge-corporate"
        st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<h3 style="color:#1E2A38; font-weight:700;">{st.session_state["current_analysis_title"]} Executive Minutes</h3>'
                    f'<span class="{badge_class}">{m_type}</span></div>', unsafe_allow_html=True)
        
        # Top Metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Session Date", st.session_state['ts'])
        with m2:
            st.metric("Assignments Tracking", len(st.session_state['actions'].split('•'))-1)
        with m3:
            st.metric("Transcript Coverage", f"{len(st.session_state['current_transcript'])} chars")

        # Executive Output Cards
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        
        # Summary column
        with c1:
            st.markdown(f"<h4 style='color:#4F7CFF;'>📄 Summary of Key Discussion</h4>", unsafe_allow_html=True)
            st.write(st.session_state['summary'])
        
        # Actions column
        with c2:
            st.markdown(f"<h4 style='color:#10B981;'>🎯 Task Assignments & Deadlines</h4>", unsafe_allow_html=True)
            st.write(st.session_state['actions'])
        st.markdown('</div>', unsafe_allow_html=True)

        # PDF Download
        pdf_file = generate_pro_pdf(st.session_state["current_analysis_title"], st.session_state['summary'], st.session_state['actions'], st.session_state['ts'], m_type)
        with open(pdf_file, "rb") as f:
            st.download_button("📥 Download Official Report (PDF)", f, file_name=f"{st.session_state['current_analysis_title'].replace(' ', '_')}_MoM.pdf", type="secondary", use_container_width=True)

        # --- PINPOINT SMART QUERY ENGINE ---
        st.divider()
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='color:#1E2A38; font-weight:700; margin-bottom:1rem;'>💬 Consult the Strategic Advisor</h4>", unsafe_allow_html=True)
        st.write("Ask a specific question about discussed roles, deadlines, project specifics, or consensus points.")
        
        col_q1, col_q2 = st.columns([4,1])
        with col_q1:
            user_q = st.text_input("Ask about Rahul's role, deadlines, or specific decisions...", key="live_q", placeholder="What did Rahul decide about the Interstellar January project?")
        with col_q2:
            st.write("")
            st.write("")
            ask_btn = st.button("Query Advisor", type="secondary", use_container_width=True)
        
        if (user_q and ask_btn) or (user_q and 'live_q' in st.session_state):
            ctx = st.session_state['current_transcript']
            # Pinpoint search logic
            sentences = [s.strip() for s in ctx.split('.') if len(s.strip()) > 5]
            query_words = [w.lower() for w in user_q.split() if len(w) > 3]
            matches = [s for s in sentences if any(w in s.lower() for w in query_words)]

            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                # Provide pinpoint context, avoiding initial generic introduction
                st.write(f"**Advisor Response:** Based on the transcript: *{'. '.join(matches[:2])}*")
            else:
                st.write("**Advisor Response:** I was unable to find specific details answering that question in this session context. Try broader keywords.")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Historical Archives":
    st.markdown("""
    <div class="hero-banner" style="padding: 2rem; background-image: linear-gradient(rgba(15, 23, 42, 0.8), rgba(15, 23, 42, 0.8)), 
                          url('https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=2070');">
        <h1>Historical Archives</h1>
        <p>Review discussed decisions, previous assignments, and long-term project intelligence.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Secure DB retrieval
    try:
        conn = sqlite3.connect('strategic_intel_v8.db')
        data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    except sqlite3.Error as e:
        st.error(f"Error connecting to archives: {e}")
        data = []
    finally:
        conn.close()
    
    if not data: 
        st.info("No processed records found. Go to 'New Intelligence' to analyze your first session.")
    else:
        st.markdown('<div style="margin-top:2rem;">', unsafe_allow_html=True)
        for row in data:
            # Badge for type
            badge_class = "badge-academic" if "Academic" in row[3] else "badge-corporate"
            header = f"📅 {row[1]} | {row[2]} <span class='{badge_class}' style='margin-left:10px;'>{row[3]}</span>"
            
            with st.expander(header, expanded=False):
                col1, col2 = st.columns([6, 1])
                with col1: 
                    st.markdown(f"<h5 style='color:#4F7CFF; margin-top:1rem;'>Discussion Summary</h5>", unsafe_allow_html=True)
                    st.write(row[4])
                    st.markdown(f"<h5 style='color:#10B981;'>Tracked Assignments</h5>", unsafe_allow_html=True)
                    st.write(row[5])
                with col2:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Delete", key=f"d_{row[0]}", type="secondary", use_container_width=True): 
                        delete_record(row[0]) 
                        st.rerun() # Refresh list instantly
        st.markdown('</div>', unsafe_allow_html=True)
