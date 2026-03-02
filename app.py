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

# --- 3. PREMIUM SaaS UI/UX ---
st.set_page_config(page_title="Strategic Intel", layout="wide", page_icon="💼")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC !important; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; color: white !important; }
    .executive-card {
        background: white; padding: 2.5rem; border-radius: 16px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 2rem; color: #1E293B;
    }
    .main-title { color: #1E2A38; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
    .sub-title { color: #64748B; font-size: 16px; margin-bottom: 32px; }
    .ai-bubble {
        background-color: #F1F5F9; border-left: 5px solid #4F7CFF;
        padding: 1.5rem; border-radius: 12px; margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>💼 Workspace</h2>", unsafe_allow_html=True)
    m_type = st.selectbox("Meeting Classification", ["Corporate Meeting", "Academic Class", "Strategy Sync"])
    st.markdown("---")
    choice = st.radio("Navigation", ["🚀 Intelligence Suite", "📅 Meeting Archives"], label_visibility="collapsed")

# --- TAB 1: INTELLIGENCE SUITE + PINPOINT QUERY ---
if choice == "🚀 Intelligence Suite":
    st.markdown(f'<h1 class="main-title">{m_type} Suite</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Synthesize recordings and query context with pinpoint accuracy.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Audio or Video", type=["mp3", "wav", "mp4", "m4a", "mov"], label_visibility="collapsed")
    
    if file:
        if file.type.startswith('video'): st.video(file) # Video Preview Feature
        else: st.audio(file)
            
    title = st.text_input("Session Reference", placeholder="e.g. Q1 Operations Review")
    
    if file and st.button("🚀 Process Intelligence"):
        with st.spinner("AI is decoding meeting context and strategic intent..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # AI Processing
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Store for Live Query logic
            st.session_state['current_transcript'] = raw_text

            # Adaptive Intent Extraction
            patterns = r"([^.]*(?:monday|friday|deadline|will|must|homework|assignment|submit|due|by|tasked|decided)[^.]*\.)"
            actions = "\n".join([f"• {a.strip()}" for a in re.findall(patterns, raw_text, re.I)])

            # Executive Summarization
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # Database Sync
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel_v8.db')
            conn.execute("INSERT INTO archives (date, title, type, summary, actions, transcript) VALUES (?,?,?,?,?,?)",
                         (ts, title, m_type, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.session_state['summary'] = summary
            st.session_state['actions'] = actions
            st.session_state['ts'] = ts
            st.success("Intelligence Synchronized!")

    # --- INTEGRATED "PINPOINT" QUERY BOX ---
    if 'current_transcript' in st.session_state:
        st.markdown("---")
        st.markdown("### 🎯 Executive Synthesis")
        c1, c2 = st.columns(2)
        with c1: st.info(f"**{ '📚 Concepts' if 'Academic' in m_type else '📄 Summary' }:**\n{st.session_state['summary']}")
        with c2: st.success(f"**{ '📝 Assignments' if 'Academic' in m_type else '🎯 Actions' }:**\n{st.session_state['actions']}")

        pdf_file = generate_pro_pdf(title, st.session_state['summary'], st.session_state['actions'], st.session_state['ts'], m_type)
        with open(pdf_file, "rb") as f:
            st.download_button("📥 Download Official MoM (PDF)", f, file_name=f"{title}.pdf")

        st.markdown("### 💬 Strategic Query (Ask specific questions)")
        user_q = st.text_input("Ask about Rahul's role, deadlines, or specific decisions...", key="live_q")
        
        if user_q:
            ctx = st.session_state['current_transcript']
            # IMPROVED: Search specifically for sentences containing query keywords
            sentences = [s.strip() for s in ctx.split('.') if len(s.strip()) > 5]
            query_words = [w.lower() for w in user_q.split() if len(w) > 3]
            
            # Filter matches that actually contain the person/topic
            matches = [s for s in sentences if any(w in s.lower() for w in query_words)]

            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                # Return the relevant context, skipping the generic intro
                st.write(f"**Advisor Response:** Based on the transcript, {'. '.join(matches[:2])}.")
            else:
                st.write("**Advisor Response:** I found the meeting context, but no specific mention of those terms. Try using a specific name or keyword.")
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES ---
elif choice == "📅 Meeting Archives":
    st.markdown('<h1 class="main-title">Intelligence Archives</h1>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_v8.db')
    data = conn.execute("SELECT id, date, title, type, summary, actions FROM archives ORDER BY id DESC").fetchall()
    if not data: st.info("Processed records will appear here.")
    else:
        for row in data:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([4, 1.5, 0.5])
            with c1: 
                st.markdown(f"### {row[2]} | {row[3]}")
                st.caption(f"📅 Logged: {row[1]}")
            with c2: 
                if st.button("Review", key=f"r_{row[0]}"): 
                    st.session_state[f"e_{row[0]}"] = not st.session_state.get(f"e_{row[0]}", False)
            with c3:
                if st.button("🗑️", key=f"d_{row[0]}"): delete_record(row[0]); st.rerun()
            if st.session_state.get(f"e_{row[0]}", False):
                st.write(f"**Summary:** {row[4]}")
                st.write(f"**Action Items:** {row[5]}")
            st.markdown('</div>', unsafe_allow_html=True)
    conn.close()
