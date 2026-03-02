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

# --- 1. DATABASE SYSTEM (Universal Storage) ---
def init_db():
    conn = sqlite3.connect('universal_meetings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

def delete_entry(entry_id):
    conn = sqlite3.connect('universal_meetings.db')
    c = conn.cursor()
    c.execute("DELETE FROM archives WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()

# --- 2. PROFESSIONAL PDF ARCHITECTURE ---
def generate_pdf(title, summary, actions, date):
    pdf_path = f"MoM_{date.replace(':', '-')}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Professional Typography
    h1 = ParagraphStyle('H1', fontSize=22, textColor=colors.hexColor("#1e293b"), spaceAfter=20, fontName="Helvetica-Bold")
    h2 = ParagraphStyle('H2', fontSize=14, textColor=colors.hexColor("#2563eb"), spaceBefore=15, spaceAfter=10, fontName="Helvetica-Bold")
    body = ParagraphStyle('B', fontSize=10, leading=14)

    story.append(Paragraph("STRATEGIC MEETING SUMMARY", h1))
    story.append(Paragraph(f"<b>REFERENCE:</b> {title.upper()}", body))
    story.append(Paragraph(f"<b>TIMESTAMP:</b> {date}", body))
    story.append(Spacer(1, 25))

    story.append(Paragraph("EXECUTIVE OVERVIEW", h2))
    story.append(Paragraph(summary, body))
    story.append(Spacer(1, 20))

    story.append(Paragraph("ACTION ITEMS & DELIVERABLES", h2))
    # Table logic for structured MoM
    table_data = [["REF", "TASK DESCRIPTION / DEADLINE"]]
    for i, item in enumerate(actions.split('\n'), 1):
        if item.strip():
            table_data.append([str(i), item.strip()])

    if len(table_data) > 1:
        t = Table(table_data, colWidths=[40, 440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.hexColor("#f8fafc")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.hexColor("#1e293b")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.silver),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
    
    doc.build(story)
    return pdf_path

init_db()

# --- 3. PREMIUM UI/UX (Slate & Glass Theme) ---
st.set_page_config(page_title="Strategic Meeting Intelligence", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #0f172a; border-right: 1px solid #e2e8f0; }
    .main-header { color: #0f172a; font-size: 2.5rem; font-weight: 800; margin-bottom: 2rem; }
    
    /* Professional Card Containers */
    .content-card {
        background: white; padding: 2.5rem; border-radius: 12px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem; color: #1e293b;
    }
    .stButton>button {
        background-color: #2563eb; color: white; border-radius: 6px;
        width: 100%; border: none; font-weight: 600; padding: 0.7rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>💼 Workspace</h2>", unsafe_allow_html=True)
    mode = st.radio("Switch View", ["🚀 New Intelligence", "📅 Meeting Archives", "💬 Strategic Advisor"])
    st.markdown("---")
    st.caption("Universal Framework v5.0")

# --- TAB 1: GENERATE NEW INTELLIGENCE ---
if mode == "🚀 New Intelligence":
    st.markdown("<h1 class='main-header'>Analysis Suite</h1>", unsafe_allow_html=True)
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    
    file = st.file_uploader("Upload Meeting Audio/Video", type=["mp3", "wav", "mp4", "m4a"])
    title = st.text_input("Meeting Reference Name", placeholder="e.g. Project Delivery Discussion")
    
    if file and st.button("🚀 Process & Synthesize"):
        with st.spinner("AI is analyzing context and strategic intent..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # Transcription & Summary Engine
            w_model = whisper.load_model("base")
            result = w_model.transcribe(tmp_path)
            raw_text = result["text"]
            os.remove(tmp_path)

            # Generic Pattern Matching (Will capture Dates, Days, Deadlines)
            patterns = r"([^.]*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|will|must|deadline|by|due|schedule|complete|final|at)[^.]*\.)"
            extracted_actions = "\n".join([a.strip() for a in re.findall(patterns, raw_text, re.I)])

            # Executive Summarization
            tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
            s_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
            inputs = tokenizer("summarize: " + raw_text[:2500], return_tensors="pt", max_length=1024, truncation=True)
            sum_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, forced_bos_token_id=0)
            summary = tokenizer.decode(sum_ids[0], skip_special_tokens=True)

            # Persistent Storage
            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('universal_meetings.db')
            conn.execute("INSERT INTO archives (date, title, summary, actions, transcript) VALUES (?,?,?,?,?)",
                         (ts, title, summary, extracted_actions, raw_text))
            conn.commit()
            conn.close()

            st.success("Intelligence recorded successfully.")
            pdf_out = generate_pdf(title, summary, extracted_actions, ts)
            with open(pdf_out, "rb") as f:
                st.download_button("📥 Download Professional MoM (PDF)", f, file_name=f"{title}.pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: ARCHIVES (View & Manage) ---
elif mode == "📅 Meeting Archives":
    st.markdown("<h1 class='main-header'>Intelligence Repository</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect('universal_meetings.db')
    data = conn.execute("SELECT id, date, title, summary, actions FROM archives ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("Archives are currently empty. Process a meeting to begin.")
    else:
        for row in data:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([4, 1.2, 0.8])
            with c1:
                st.markdown(f"### {row[2]}")
                st.caption(f"📅 Record Date: {row[1]}")
            with c2:
                if st.button("Edit / Details", key=f"e_{row[0]}"):
                    st.session_state[f"edit_box_{row[0]}"] = not st.session_state.get(f"edit_box_{row[0]}", False)
            with c3:
                if st.button("🗑️ Delete", key=f"d_{row[0]}"):
                    delete_entry(row[0])
                    st.rerun()

            if st.session_state.get(f"edit_box_{row[0]}", False):
                new_s = st.text_area("Edit Summary", row[3], height=150, key=f"s_area_{row[0]}")
                new_a = st.text_area("Edit Action Items", row[4], height=150, key=f"a_area_{row[0]}")
                if st.button("Save Changes", key=f"save_btn_{row[0]}"):
                    c = conn.cursor()
                    c.execute("UPDATE archives SET summary=?, actions=? WHERE id=?", (new_s, new_a, row[0]))
                    conn.commit()
                    st.toast("Updated Successfully!")
            st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- TAB 3: STRATEGIC ADVISOR (Fixed & Functional) ---
elif mode == "💬 Strategic Advisor":
    st.markdown("<h1 class='main-header'>Contextual Intelligence</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect('universal_meetings.db')
    rows = conn.execute("SELECT title, transcript FROM archives").fetchall()
    options = {r[0]: r[1] for r in rows} # Fixed Indexing
    
    if options:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        selection = st.selectbox("Select Meeting Archive", list(options.keys()))
        query = st.text_input("Ask a question about the decisions in this meeting...")
        
        if query:
            context = options[selection]
            # Semantic keyword scanning
            results = [s for s in context.split('.') if any(w.lower() in s.lower() for w in query.split())]
            if results:
                st.info(f"**AI Insight:** {'. '.join(results[:2])}.")
            else:
                st.warning("No specific mention found. Try using keywords like 'budget', 'deadline', or 'final'.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Please process a recording first to enable the Strategic Advisor.")
    conn.close()
