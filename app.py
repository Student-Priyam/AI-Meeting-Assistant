import streamlit as st
import whisper
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import sqlite3
import re
import tempfile
import os
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import datetime
import networkx as nx
from collections import Counter
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# Download NLTK data for summarization
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# ==========================================
# 1. CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Strategic Intel | Executive Briefing", layout="wide", page_icon="🧠")

# "Executive Slate" Design System
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    div[data-testid="stVerticalBlock"] > div > div {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    h1, h2, h3 { color: #1E2A38 !important; font-family: 'Helvetica Neue', sans-serif; }
    .stButton>button {
        background-color: #1E2A38; color: white; border-radius: 4px; border: none;
    }
    .stButton>button:hover { background-color: #334155; }
    .stProgress > div > div > div > div { background-color: #10B981; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE MANAGER
# ==========================================
class StrategicDB:
    def __init__(self, db_name="strategic_intel_final.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                upload_date TIMESTAMP,
                mode TEXT,
                transcript TEXT,
                summary TEXT,
                assignments TEXT,
                intel_data TEXT
            )
        ''')
        self.conn.commit()

    def save_meeting(self, filename, mode, transcript, summary, assignments, intel_data):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO meetings (filename, upload_date, mode, transcript, summary, assignments, intel_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filename, datetime.datetime.now(), mode, transcript, summary, assignments, intel_data))
        self.conn.commit()

    def get_history(self):
        return pd.read_sql("SELECT * FROM meetings ORDER BY id DESC", self.conn)

    def delete_meeting(self, meeting_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        self.conn.commit()

db = StrategicDB()

# ==========================================
# 3. PERFORMANCE-OPTIMIZED AI ENGINE
# ==========================================

@st.cache_resource
def load_whisper_model(model_size="tiny"):
    """Load Whisper model - 'tiny' is 3x faster than 'base' with good accuracy."""
    try:
        model = whisper.load_model(model_size)
        return model
    except Exception as e:
        st.error(f"Failed to load Whisper model: {e}")
        return None

@st.cache_resource
def load_summarizer():
    """Load DistilBART for high-quality summaries."""
    try:
        model_name = "sshleifer/distilbart-cnn-12-6"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        device = 0 if torch.cuda.is_available() else -1
        if device >= 0:
            model = model.to(device)
        return tokenizer, model, device
    except Exception as e:
        st.error(f"Failed to load summarizer: {e}")
        return None, None, -1

# --- FAST EXTRACTOR: TextRank Algorithm (Instant) ---
def extractive_summary_fast(text, num_sentences=5):
    """Fast extractive summarization using TextRank algorithm."""
    try:
        sentences = sent_tokenize(text)
        if len(sentences) <= num_sentences:
            return text
        
        # Tokenize and create word frequencies
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text.lower())
        word_freq = Counter([w for w in words if w.isalnum() and w not in stop_words])
        
        # Score sentences based on word frequencies
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            sentence_words = word_tokenize(sentence.lower())
            if sentence_words:
                score = sum(word_freq.get(w, 0) for w in sentence_words) / len(sentence_words)
                sentence_scores[i] = score
        
        # Get top sentences
        top_indices = sorted(sentence_scores.keys(), key=lambda x: sentence_scores[x], reverse=True)[:num_sentences]
        top_indices.sort()
        
        summary = ' '.join([sentences[i] for i in top_indices])
        return summary
    except Exception as e:
        return text[:500] + "..."

# --- HIGH-QUALITY SUMMARIZER: DistilBART ---
def summarize_with_bart(text, tokenizer, model, device):
    """Generate abstractive summary using DistilBART."""
    if not text or len(text.strip()) < 100:
        return text if text else "Text too short."
    
    # Process in chunks
    max_chunk = 1024
    chunks = [text[i:i+max_chunk] for i in range(0, min(len(text), 3000), max_chunk)]
    
    summaries = []
    for chunk in chunks:
        if len(chunk) < 50:
            continue
        try:
            inputs = tokenizer(chunk, return_tensors="pt", max_length=1024, truncation=True)
            if device >= 0:
                inputs = {k: v.to(device) for k, v in inputs.items()}
            
            summary_ids = model.generate(
                inputs["input_ids"],
                max_length=130,
                min_length=30,
                num_beams=4,
                length_penalty=2.0,
                early_stopping=True
            )
            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            summaries.append(summary)
        except Exception:
            continue
    
    return " ".join(summaries) if summaries else extractive_summary_fast(text)

# --- INTENT EXTRACTION ---
def extract_assignments(text):
    """Extract action items using pattern matching."""
    assignments = []
    
    # Multiple patterns for different command structures
    patterns = [
        r"([A-Z][a-z]+),?\s(?:please|can you|need to|should|will you|must)\s(.+?)(?:\.|$)",
        r"([A-Z][a-z]+),?\s(go ahead and|start working on|finish|complete)\s(.+?)(?:\.|$)",
        r"action item[:\s]+([A-Z][a-z]+)[:\s]+(.+?)(?:\.|$)",
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) == 2:
                recipient, action = match.groups()
            elif len(match.groups()) == 3:
                recipient, _, action = match.groups()
            else:
                continue
            assignments.append(f"👤 {recipient.strip()}: {action.strip().capitalize()}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_assignments = []
    for a in assignments:
        if a.lower() not in seen:
            seen.add(a.lower())
            unique_assignments.append(a)
    
    return unique_assignments

# ==========================================
# 4. VIDEO PROCESSING PIPELINE
# ==========================================
def process_video_fast(uploaded_file, mode, quality_mode="fast"):
    """Optimized processing pipeline with progress tracking."""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Save temp file
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    try:
        tfile.write(uploaded_file.read())
        status_text.text("Step 1/3: Transcribing audio with Whisper...")
        progress_bar.progress(20)
        
        # Transcription
        result = whisper_model.transcribe(tfile.name)
        transcript_text = result['text']
        progress_bar.progress(50)
        
        if quality_mode == "fast":
            status_text.text("Step 2/3: Generating extractive summary...")
            summary = extractive_summary_fast(transcript_text)
        else:
            status_text.text("Step 2/3: Generating abstractive summary (DistilBART)...")
            summary = summarize_with_bart(transcript_text, tokenizer, summarizer_model, device)
        
        progress_bar.progress(75)
        
        # Extract assignments
        status_text.text("Step 3/3: Identifying action items...")
        assignments = extract_assignments(transcript_text)
        
        # Intel data
        intel_data = {
            "speakers_detected": len(set(re.findall(r"([A-Z][a-z]+)", transcript_text[:500]))),
            "action_items_count": len(assignments),
            "transcript_length": len(transcript_text),
            "processing_mode": quality_mode
        }
        
        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")
        
        return transcript_text, summary, assignments, intel_data
        
    finally:
        try:
            os.unlink(tfile.name)
        except:
            pass

# ==========================================
# 5. PDF GENERATOR
# ==========================================
def create_pdf(filename, summary, assignments):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"STRATEGIC BRIEFING: {filename}", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("Executive Summary", styles['Heading2']))
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("Strategic Deliverables & Assignments", styles['Heading2']))
    data = [['Recipient', 'Action Required']]
    
    if assignments:
        for item in assignments:
            clean_item = item.replace("👤 ", "").split(":")
            if len(clean_item) > 1:
                data.append([clean_item[0], clean_item[1].strip()])
            else:
                data.append(["Unassigned", clean_item[0]])
    else:
        data.append(["N/A", "No explicit assignments detected."])

    t = Table(data, colWidths=[150, 350])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.5)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# 6. MAIN APPLICATION
# ==========================================

st.title("Strategic Intel 🧠")
st.caption("High-Performance Intelligence Extraction System")

with st.sidebar:
    st.header("Workspace Settings")
    mode = st.radio("Intelligence Mode:", ["Corporate Strategy", "Academic Review"])
    
    st.markdown("---")
    st.header("Performance Settings")
    quality_mode = st.selectbox(
        "Processing Mode:",
        ["fast", "deep"],
        format_func=lambda x: "⚡ Fast (TextRank)" if x == "fast" else "🎯 Deep (AI Summarization)"
    )
    st.info(
        "⚡ **Fast**: Instant results using TextRank algorithm\n\n"
        "🎯 **Deep**: High-quality AI summaries (2-3x slower)"
    )
    
    st.markdown("---")
    st.header("Model Selection")
    whisper_size = st.selectbox("Whisper Model:", ["tiny", "base", "small"], index=0)
    
    if st.button("🔄 Reload Models"):
        st.cache_resource.clear()
        st.rerun()
    
    st.markdown("---")
    st.markdown("**System Status:**")
    if whisper_model is None:
        st.error("Whisper not loaded")
    else:
        st.success("Whisper Ready")

# Load models based on selection
@st.cache_resource
def get_models(size):
    return load_whisper_model(size)

whisper_model = get_models(whisper_size)
tokenizer, summarizer_model, device = load_summarizer()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📂 Ingest", "📊 Dashboard", "🗣️ Advisor", "🗄️ Archives"])

# --- TAB 1: INGEST ---
with tab1:
    uploaded_file = st.file_uploader("Upload Meeting/Class Recording (.mp4, .mov)", type=["mp4", "mov"])
    
    if uploaded_file is not None:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.video(uploaded_file)
        with col2:
            st.write("**File Details:**")
            st.write(f"📁 {uploaded_file.name}")
            st.write(f"📊 {(uploaded_file.size / 1024 / 1024):.2f} MB")
            
            st.markdown("---")
            st.write("**Recommended Mode:**")
            if uploaded_file.size < 5 * 1024 * 1024:  # < 5MB
                st.success("Small file - Fast mode ideal")
            elif uploaded_file.size < 20 * 1024 * 1024:  # < 20MB
                st.warning("Medium file - Balanced mode recommended")
            else:
                st.error("Large file - May take time")
        
        st.markdown("---")
        if st.button("🚀 Extract Intelligence", type="primary"):
            transcript, summary, assignments, intel = process_video_fast(uploaded_file, mode, quality_mode)
            
            db.save_meeting(
                uploaded_file.name, mode, transcript, 
                summary, str(assignments), str(intel)
            )
            
            st.session_state['latest_result'] = {
                'transcript': transcript,
                'summary': summary,
                'assignments': assignments,
                'filename': uploaded_file.name
            }
            st.success("✅ Intelligence Extraction Complete!")
            st.rerun()

# --- TAB 2: DASHBOARD ---
with tab2:
    if 'latest_result' in st.session_state:
        res = st.session_state['latest_result']
        
        # Quick Stats
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Transcript", f"{len(res['transcript'])} chars")
        m2.metric("Words", f"{len(res['transcript'].split())}")
        m3.metric("Assignments", len(res['assignments']))
        m4.metric("Mode", quality_mode.upper())
        
        # Tabs within Dashboard
        d_tab1, d_tab2 = st.tabs(["📋 Summary", "📝 Transcript"])
        
        with d_tab1:
            st.subheader("Executive Summary")
            st.info(res['summary'])
            
            st.subheader("🎯 Action Items")
            if res['assignments']:
                for i, item in enumerate(res['assignments'], 1):
                    st.write(f"{i}. {item}")
            else:
                st.write("No explicit assignments detected.")
            
            # PDF Export
            pdf_data = create_pdf(res['filename'], res['summary'], res['assignments'])
            st.download_button(
                "📄 Download Strategic Brief (PDF)",
                pdf_data,
                file_name=f"Strategic_Brief_{res['filename']}.pdf",
                mime="application/pdf"
            )
        
        with d_tab2:
            with st.expander("View Full Transcript", expanded=True):
                st.text(res['transcript'])
    else:
        st.info("Upload a video in the 'Ingest' tab to begin.")

# --- TAB 3: STRATEGIC ADVISOR ---
with tab3:
    st.subheader("🗣️ Strategic Advisor")
    st.write("Ask questions about past meetings.")
    
    history_df = db.get_history()
    
    if not history_df.empty:
        query = st.text_input("Ask about the meeting:", placeholder="e.g., What did Rahul say about the budget?")
        
        if query:
            all_transcripts = " ".join(history_df['transcript'].dropna().tolist())
            sentences
