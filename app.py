import streamlit as st
import whisper
import torch
from transformers import pipeline
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

# ==========================================
# 1. CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Strategic Intel | Executive Briefing", layout="wide", page_icon="🧠")

# "Executive Slate" Design System
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #F8FAFC;
    }
    /* Card Styling */
    div[data-testid="stVerticalBlock"] > div > div {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    /* Typography */
    h1, h2, h3 {
        color: #1E2A38 !important; /* Midnight Blue */
        font-family: 'Helvetica Neue', sans-serif;
    }
    /* Buttons */
    .stButton>button {
        background-color: #1E2A38;
        color: white;
        border-radius: 4px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #334155;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #E2E8F0;
        border-radius: 4px 4px 0px 0px;
        color: #1E2A38;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE MANAGER (SQLite)
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

    def update_record(self, meeting_id, column, value):
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE meetings SET {column} = ? WHERE id = ?", (value, meeting_id))
        self.conn.commit()

db = StrategicDB()

# ==========================================
# 3. AI ENGINE (The "Who" & "To Whom")
# ==========================================
@st.cache_resource
def load_models():
    # Whisper Base for speed/accuracy balance
    whisper_model = whisper.load_model("base")
    # DistilBART for summarization
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=0 if torch.cuda.is_available() else -1)
    return whisper_model, summarizer

whisper_model, summarizer = load_models()

def extract_speaker_intent(full_text):
    """
    Layer 1 & 2 Logic:
    1. Identifies Proper Nouns (Potential Speakers).
    2. Regex for Assignments (Who -> To Whom).
    """
    assignments = []
    
    # Regex Pattern: [Name], [Modal/Command] [Action]
    # Matches: "Sarah, please send the report" or "John, can you update the slide?"
    pattern = r"([A-Z][a-z]+),?\s(?:please|can you|need to|should|will you)\s(.+?)(?:\.|$)"
    
    matches = re.finditer(pattern, full_text)
    
    for match in matches:
        recipient = match.group(1)
        action = match.group(2)
        assignments.append(f"👤 {recipient}: {action.strip().capitalize()}...")
    
    return assignments

def process_video(uploaded_file, mode):
    """
    Core Processing Pipeline:
    1. Save Temp File
    2. Transcribe (Whisper)
    3. Analyze (Summarization + Regex)
    4. Structure Data
    """
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') 
    tfile.write(uploaded_file.read())
    
    # 1. Transcription
    result = whisper_model.transcribe(tfile.name)
    transcript_text = result['text']
    
    # 2. Summarization (Chunking for BART limit)
    # BART limit is 1024 tokens, we chunk text to ~1000 chars
    chunks = [transcript_text[i:i+1000] for i in range(0, len(transcript_text), 1000)]
    summary = ""
    for chunk in chunks:
        if len(chunk) > 50: # Avoid empty chunks
            summary += summarizer(chunk, max_length=130, min_length=30, do_sample=False)[0]['summary_text'] + " "

    # 3. Assignment Extraction
    assignments = extract_speaker_intent(transcript_text)
    
    # 4. Strategic Intel Construction
    intel_data = {
        "speakers_detected": len(set(re.findall(r"([A-Z][a-z]+)", transcript_text[:500]))), # Heuristic
        "action_items_count": len(assignments),
        "duration_estimate": "Unknown (Video processing required for duration)"
    }

    return transcript_text, summary, assignments, intel_data

# ==========================================
# 4. DOCUMENT ENGINE (ReportLab)
# ==========================================
def create_pdf(filename, summary, assignments):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    elements.append(Paragraph(f"STRATEGIC BRIEFING: {filename}", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # Executive Summary
    elements.append(Paragraph("Executive Summary", styles['Heading2']))
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 24))

    # Action Items Table
    elements.append(Paragraph("Strategic Deliverables & Assignments", styles['Heading2']))
    data = [['Recipient', 'Action Required']] # Header
    
    if assignments:
        for item in assignments:
            # Clean formatting: "👤 Name: Action..."
            clean_item = item.replace("👤 ", "").split(":")
            if len(clean_item) > 1:
                data.append([clean_item[0], clean_item[1].strip()])
            else:
                data.append(["Unassigned", clean_item[0]])
    else:
        data.append(["N/A", "No explicit assignments detected."])

    t = Table(data, colWidths=[150, 350])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.5)), # Midnight Blue
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
# 5. UI CONTROLLER
# ==========================================

st.title("Strategic Intel 🧠")
st.caption("Automated Intelligence Extraction & Briefing System")

# Sidebar: Context
with st.sidebar:
    st.header("Workspace Context")
    mode = st.radio("Select Intelligence Mode:", ["Corporate Strategy", "Academic Review"])
    st.info(f"Current Mode: **{mode}**")
    st.markdown("---")
    st.markdown("**System Status:** Online")
    st.markdown("**Model:** Whisper Base + DistilBART")

# Main Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📂 Ingest", "📊 Dashboard", "🗣️ Strategic Advisor", "🗄️ Archives"])

# --- TAB 1: INGEST ---
with tab1:
    uploaded_file = st.file_uploader("Upload Meeting/Class Recording (.mp4, .mov)", type=["mp4", "mov"])
    
    if uploaded_file is not None:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.video(uploaded_file)
        with col2:
            st.write("**File Details:**")
            st.write(f"Name: {uploaded_file.name}")
            st.write(f"Size: {uploaded_file.size / 1024:.2f} KB")
            
        if st.button("🚀 Extract Intelligence"):
            with st.spinner("Analyzing Audio Stream & Semantic Intent
