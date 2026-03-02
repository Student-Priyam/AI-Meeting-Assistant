<think>
The user is getting a syntax error because there's corrupted text in the file. They want a generic, clean version of the code that works properly. Let me create a completely clean, properly formatted version that:

1. Has no corrupted text
2. Is generic (not specific to any particular use case)
3. Works on Streamlit Cloud
4. Uses AI models for efficient output

Let me write the complete, clean code from scratch.

</think># Strategic Intel: Clean Generic Version

Here's the complete, clean code with no corrupted text:

## 1. `requirements.txt`

```
streamlit>=1.28.0
pandas>=2.1.0
reportlab>=4.0.0
openai>=1.0.0
```

## 2. `app.py`

```python
import streamlit as st
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
from collections import Counter
import json
from openai import OpenAI

st.set_page_config(
    page_title="Strategic Intel | AI Briefing System", 
    layout="wide", 
    page_icon="🧠"
)

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
        padding: 0.5rem 1rem; font-weight: 500;
    }
    .stButton>button:hover { background-color: #334155; color: white; }
    [data-testid="stMetricValue"] { color: #1E2A38; }
    [data-testid="stMetricLabel"] { color: #64748B; }
    .stProgress > div > div > div > div { background-color: #10B981; }
    .stSuccess { background-color: #D1FAE5; color: #065F46; border-radius: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #E2E8F0; border-radius: 4px 4px 0px 0px; color: #1E2A38;
    }
    [data-testid="stSidebar"] { background-color: #1E2A38; }
    [data-testid="stSidebar"] * { color: #F8FAFC !important; }
    </style>
""", unsafe_allow_html=True)

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

def get_openai_client():
    if 'openai_api_key' in st.session_state and st.session_state['openai_api_key']:
        return OpenAI(api_key=st.session_state['openai_api_key'])
    return None

def transcribe_audio(client, audio_file):
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return transcript.text
    except Exception as e:
        st.error(f"Transcription error: {e}")
        return None

def generate_summary(client, transcript, mode):
    if mode == "Corporate Strategy":
        system_prompt = """You are an executive assistant. Create a concise strategic summary 
        with: 1) Key decisions made, 2) Strategic priorities, 3) Financial/budget implications, 
        4) Action items with owners. Format as bullet points."""
    else:
        system_prompt = """You are an academic tutor. Create a summary with: 
        1) Core concepts covered, 2) Important dates/deadlines, 3) Assignments/homework, 
        4) Topics to review. Format as bullet points."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcript:\n\n{transcript[:10000]}"}
            ],
            max_tokens=500,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Summarization error: {e}")
        return None

def extract_assignments_ai(client, transcript):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Extract all action items and assignments from the transcript.
                For each item, identify: WHO is responsible, WHAT needs to be done, and any DEADLINE.
                Return as a JSON array with objects containing: recipient, action, deadline.
                If no deadline mentioned, set to 'ASAP'.
                Example: [{"recipient": "Sarah", "action": "Finalize budget report", "deadline": "Friday"}]"""},
                {"role": "user", "content": f"Transcript:\n\n{transcript[:8000]}"}
            ],
            max_tokens=1000,
            temperature=0.2
        )
        
        try:
            assignments_data = json.loads(response.choices[0].message.content)
            assignments = []
            for item in assignments_data:
                assignments.append(f"👤 {item['recipient']}: {item['action']} (Due: {item['deadline']})")
            return assignments
        except:
            return [f"👤 {response.choices[0].message.content}"]
            
    except Exception as e:
        st.error(f"Assignment extraction error: {e}")
        return []

def answer_question(client, question, all_transcripts):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are a strategic advisor. Answer questions based 
                ONLY on the provided meeting transcripts. Be specific and cite the context."""},
                {"role": "user", "content": f"Question: {question}\n\nTranscripts:\n\n{all_transcripts[:15000]}"}
            ],
            max_tokens=500,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def simple_summarize(text, num_sentences=5):
    if not text or len(text.strip()) < 50:
        return text if text else "Text too short to summarize."
    
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if len(sentences) <= num_sentences:
        return text
    
    words = text.lower().split()
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
                  'into', 'through', 'during', 'before', 'after', 'above', 'below',
                  'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either', 'neither',
                  'not', 'only', 'just', 'also', 'very', 'too', 'quite', 'rather'}
    
    word_freq = Counter([w for w in words if w not in stop_words and len(w) > 2])
    
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        sentence_words = sentence.lower().split()
        if sentence_words:
            score = sum(word_freq.get(w, 0) for w in sentence_words) / len(sentence_words)
            if re.search(r'\d+', sentence):
                score *= 1.5
            if re.search(r'[A-Z][a-z]+', sentence):
                score *= 1.2
            sentence_scores[i] = score
    
    top_indices = sorted(sentence_scores.keys(), key=lambda x: sentence_scores[x], reverse=True)[:num_sentences]
    top_indices.sort()
    
    return '. '.join([sentences[i] for i in top_indices]) + '.'

def extract_assignments(text):
    assignments = []
    
    patterns = [
        r"([A-Z][a-z]+),?\s+(?:please|can you|need to|should|will you|must)\s+(.+?)(?:\.|$)",
        r"(?:action item|action)[:\s]+([A-Z][a-z]+)[:\s]+(.+?)(?:\.|$)",
        r"([A-Z][a-z]+)\s+(?:will|is going to|should|must)\s+(.+?)(?:\.|$)",
        r"(?:assigned to|owner)[:\s]+([A-Z][a-z]+)[:\s]+(.+?)(?:\.|$)",
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            groups = match.groups()
            if len(groups) >= 2:
                recipient, action = groups[0], groups[1]
                action = re.sub(r'\s+', ' ', action).strip()
                if len(action) > 5:
                    assignments.append(f"👤 {recipient.strip()}: {action.strip().capitalize()}")
    
    seen = set()
    unique_assignments = []
    for a in assignments:
        if a.lower() not in seen:
            seen.add(a.lower())
            unique_assignments.append(a)
    
    return unique_assignments

def generate_sample_intelligence(filename, mode):
    return f"""
    Welcome to today's {mode} session. This is a comprehensive overview of recent developments.
    The team has made significant progress on multiple fronts. Rahul will present the key findings.
    Sarah, please take notes for the follow-up documentation. John has prepared the quarterly report.
    Lisa, can you distribute it to all stakeholders? The main topics include project timelines and resource allocation.
    Mike will address any technical challenges. Action item: Rahul - present findings.
    Action item: Sarah - distribute documentation. Action item: John - finalize quarterly report.
    We have achieved our targets for this period. Next review scheduled for next week.
    """

def create_pdf(filename, summary, assignments, intel_data):
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
    data = [['Recipient', 'Action Required', 'Deadline']]
    
    if assignments:
        for item in assignments:
            parts = item.replace("👤 ", "").split(":")
            if len(parts) > 1:
                action_parts = parts[1].split("(Due:")
                action = action_parts[0].strip()
                deadline = action_parts[1].replace(")", "").strip() if len(action_parts) > 1 else "ASAP"
                data.append([parts[0].strip(), action, deadline])
            else:
                data.append(["Unassigned", parts[0], "ASAP"])
    else:
        data.append(["N/A", "No explicit assignments detected.", "N/A"])

    t = Table(data, colWidths=[120, 280, 100])
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

def process_video(uploaded_file, mode, use_ai=True):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Step 1/4: Preparing file...")
        progress_bar.progress(10)
        
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tfile.write(uploaded_file.read())
        audio_path = tfile.name
        tfile.close()
        
        status_text.text("Step 2/4: Transcribing audio...")
        progress_bar.progress(30)
        
        client = get_openai_client()
        
        if use_ai and client:
            with open(audio_path, 'rb') as audio_file:
                transcript = transcribe_audio(client, audio_file)
            
            if not transcript:
                transcript = generate_sample_intelligence(uploaded_file.name, mode)
        else:
            transcript = generate_sample_intelligence(uploaded_file.name, mode)
            st.info("Using demo mode (add API key for real transcription)")
        
        status_text.text("Step 3/4: Analyzing intelligence...")
        progress_bar.progress(60)
        
        if use_ai and client:
            summary = generate_summary(client, transcript, mode)
            if not summary:
                summary = simple_summarize(transcript)
            assignments = extract_assignments_ai(client, transcript)
            if not assignments:
                assignments = extract_assignments(transcript)
        else:
            summary = simple_summarize(transcript)
            assignments = extract_assignments(transcript)
        
        status_text.text("Step 4/4: Compiling results...")
        progress_bar.progress(90)
        
        intel_data = {
            "file_size": f"{uploaded_file.size / 1024:.1f} KB",
            "assignments_count": len(assignments),
            "mode": mode,
            "ai_powered": use_ai and client is not None
        }
        
        progress_bar.progress(100)
        status_text.text("Processing complete!")
        
        return transcript, summary, assignments, intel_data
        
    except Exception as e:
        status_text.text(f"Error: {str(e)}")
        raise e
    finally:
        try:
            os.unlink(audio_path)
        except:
            pass

st.title("Strategic Intel")
st.caption("AI-Powered Meeting Intelligence System")

with st.sidebar:
    st.header("Settings")
    mode = st.radio("Mode:", ["Corporate Strategy", "Academic Review"])
    
    st.markdown("---")
    st.header("AI Configuration")
    api_key = st.text_input("OpenAI API Key:", type="password")
    if api_key:
        st.session_state['openai_api_key'] = api_key
        st.success("API Key configured!")
    
    st.markdown("---")
    st.header("Processing Options")
    use_ai = st.checkbox("Use AI Processing", value=True, disabled=not api_key)
    st.info("Without API key, demo mode will be used.")

tab1, tab2, tab3, tab4 = st.tabs(["Ingest", "Dashboard", "Advisor", "Archives"])

with tab1:
    uploaded_file = st.file_uploader("Upload Meeting/Class Recording", type=["mp4", "mov", "mp3", "wav"])
    
    if uploaded_file is not None:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.video(uploaded_file)
        with col2:
            st.write("File:", uploaded_file.name)
            st.write("Size:", f"{uploaded_file.size / 1024:.1f} KB")
        
        if st.button("Extract Intelligence", type="primary"):
            transcript, summary, assignments, intel = process_video(uploaded_file, mode, use_ai)
            
            db.save_meeting(
                uploaded_file.name, mode
