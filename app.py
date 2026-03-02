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

# --- 1. SYSTEM INITIALIZATION ---
def init_db():
    conn = sqlite3.connect('strategic_intel_v5.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS archives 
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, summary TEXT, actions TEXT, transcript TEXT)''')
    conn.commit()
    conn.close()

def delete_record(record_id):
    conn = sqlite3.connect('strategic_intel_v5.db')
    conn.execute("DELETE FROM archives WHERE id=?", (record_id,))
    conn.commit()
    conn.close()

# --- 2. EXECUTIVE PDF ENGINE (CRASH-PROOF) ---
def generate_pro_pdf(title, summary, actions, date):
    pdf_path = f"Executive_MoM_{date.replace(':', '-')}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Premium Styles
    h1 = ParagraphStyle('H1', fontSize=24, textColor=colors.Color(0.12, 0.16, 0.22), spaceAfter=20, fontName="Helvetica-Bold")
    h2 = ParagraphStyle('H2', fontSize=14, textColor=colors.Color(0.31, 0.49, 1), spaceBefore=15, spaceAfter=10, fontName="Helvetica-Bold")
    body = ParagraphStyle('B', fontSize=10, leading=14, fontName="Helvetica")

    story.append(Paragraph("STRATEGIC MEETING INTELLIGENCE", h1))
    story.append(Paragraph(f"<b>REFERENCE:</b> {title.upper()}", body))
    story.append(Paragraph(f"<b>TIMESTAMP:</b> {date}", body))
    story.append(Spacer(1, 25))

    story.append(Paragraph("STRATEGIC SUMMARY", h2))
    story.append(Paragraph(summary, body))
    story.append(Spacer(1, 20))

    story.append(Paragraph("ACTIONABLE DELIVERABLES", h2))
    table_data = [["REF", "TASK / DEADLINE"]]
    for i, item in enumerate(actions.split('\n'), 1):
        if item.strip():
            table_data.append([str(i), item.strip()])

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

# --- 3. PREMIUM SAAS UI/UX ---
st.set_page_config(page_title="Strategic Meeting Intelligence", layout="wide", page_icon="💼")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC !important; }
    
    /* Executive Cards */
    .executive-card {
        background: white; padding: 2.5rem; border-radius: 16px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 2rem; color: #1E293B;
    }
    
    /* Typography */
    .main-title { color: #1E2A38; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
    .sub-title { color: #64748B; font-size: 16px; margin-bottom: 32px; }
    
    /* Modern Chat Bubble */
    .ai-bubble {
        background-color: #F1F5F9; border-left: 5px solid #4F7CFF;
        padding: 1.5rem; border-radius: 12px; margin: 1rem 0; font-size: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:#1E2A38;'>💼 Enterprise Hub</h2>", unsafe_allow_html=True)
    mode = st.radio("Navigation", ["🚀 Intelligence Suite", "📅 Meeting Archives", "💬 Strategic Advisor"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("Strategic Intel v5.0 • Enterprise Edition")

# --- TAB 1: INTELLIGENCE SUITE ---
if mode == "🚀 Intelligence Suite":
    st.markdown('<h1 class="main-title">Turn Meetings Into Strategic Insights</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Upload your meeting and generate structured summaries instantly.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    file = st.file_uploader("Upload Recording", type=["mp3", "wav", "mp4", "m4a"], label_visibility="collapsed")
    title = st.text_input("Meeting Subject / Project Reference", placeholder="e.g. Annual Strategy Review")
    
    if file and st.button("🚀 Process Intelligence"):
        with st.spinner("AI is synthesizing strategic context..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name

            # AI Analysis
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

            ts = datetime.now().strftime("%d-%m-%Y %H:%M")
            conn = sqlite3.connect('strategic_intel_v5.db')
            conn.execute("INSERT INTO archives (date, title, summary, actions, transcript) VALUES (?,?,?,?,?)",
                         (ts, title, summary, actions, raw_text))
            conn.commit()
            conn.close()

            st.success("Analysis Complete!")
            pdf_out = generate_pro_pdf(title, summary, actions, ts)
            with open(pdf_out, "rb") as f:
                st.download_button("📥 Download Official MoM", f, file_name=f"{title}.pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: MEETING ARCHIVES ---
elif mode == "📅 Meeting Archives":
    st.markdown('<h1 class="main-title">Intelligence Archives</h1>', unsafe_allow_html=True)
    conn = sqlite3.connect('strategic_intel_v5.db')
    data = conn.execute("SELECT id, date, title, summary, actions FROM archives ORDER BY id DESC").fetchall()
    
    if not data:
        st.info("Your processed meetings will appear here.")
    else:
        for row in data:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([4, 1.5, 0.5])
            with c1:
                st.markdown(f"### {row[2]}")
                st.caption(f"📅 {row[1]} • Processed")
            with c2:
                if st.button("Review / Edit", key=f"rev_{row[0]}"):
                    st.session_state[f"edit_{row[0]}"] = not st.session_state.get(f"edit_{row[0]}", False)
            with c3:
                if st.button("🗑️", key=f"del_{row[0]}"):
                    delete_record(row[0])
                    st.rerun()
            
            if st.session_state.get(f"edit_{row[0]}", False):
                n_s = st.text_area("Summary", row[3], height=120, key=f"ns_{row[0]}")
                n_a = st.text_area("Actions", row[4], height=120, key=f"na_{row[0]}")
                if st.button("Save Changes", key=f"sv_{row[0]}"):
                    c = conn.cursor()
                    c.execute("UPDATE archives SET summary=?, actions=? WHERE id=?", (n_s, n_a, row[0]))
                    conn.commit()
                    st.toast("Updated!")
            st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# --- TAB 3: STRATEGIC ADVISOR (FIXED DROPDOWN & Q&A) ---
elif mode == "💬 Strategic Advisor":
    st.markdown('<h1 class="main-title">Strategic Advisor</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Query past meeting intelligence using natural language.</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('strategic_intel_v5.db')
    rows = conn.execute("SELECT title, transcript FROM archives").fetchall()
    # Correct mapping for dropdown
    options = {r[0]: r[1] for r in rows} 
    
    if options:
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        # Dropdown fix
        selected_m = st.selectbox("Choose Meeting Context", list(options.keys()))
        query = st.text_input("Consult with AI about this meeting...", placeholder="e.g. What are the next steps for Project X?")
        
        if query:
            context = options[selected_m]
            # Contextual sentence search
            matches = [s.strip() for s in context.split('.') if any(w.lower() in s.lower() for w in query.split())]
            
            st.markdown('<div class="ai-bubble">', unsafe_allow_html=True)
            if matches:
                st.write(f"**Advisor Response:** Based on '{selected_m}', here is what I found: {'. '.join(matches[:2])}.")
            else:
                st.write("**Advisor Response:** I couldn't find a direct reference. Try using broader keywords like 'deadline' or 'budget'.")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Archives are empty. Please process a meeting recording first.")
    conn.close()
