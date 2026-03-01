import streamlit as st
import whisper
from transformers import pipeline
import os

# --- 1. PAGE CONFIG & DESIGN ---
st.set_page_config(page_title="AI Meeting Minutes Pro", page_icon="🎙️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff; border-radius: 5px; padding: 10px 20px; font-weight: bold; color: #1E3A8A;
    }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; }
    .action-card { padding: 15px; border-radius: 8px; background-color: #ffffff; border-left: 5px solid #1E3A8A; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ AI-Powered Meeting Assistant")
st.markdown("*Professional Hinglish Transcription & Executive Summarization*")
st.markdown("---")

# --- 2. SMART AI LOADING ---
@st.cache_resource
def load_ai_models():
    # Whisper Base is best for Hinglish speed/accuracy balance
    w_model = whisper.load_model("base")
    # Using a reliable summarizer with explicit task definition
    try:
        s_model = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    except:
        s_model = None
    return w_model, s_model

w_model, s_model = load_ai_models()

# --- 3. SIDEBAR ---
st.sidebar.header("📁 Upload Meeting")
audio_file = st.sidebar.file_uploader("Upload Audio/Video", type=["mp3", "wav", "m4a", "mp4"])
process_btn = st.sidebar.button("🚀 Generate Minutes")

# --- 4. DATA CLEANING LOGIC ---
def clean_transcript(text):
    # Fixing common Hinglish mishearings based on your specific project context
    corrections = {
        "pream": "Priyam",
        "medium pipe": "MediaPipe",
        "fast api": "FastAPI",
        "streamlet": "Streamlit",
        "shadyul": "Schedule",
        "karna hai": "(Action Required)"
    }
    for wrong, right in corrections.items():
        text = text.replace(wrong, right).replace(wrong.capitalize(), right)
    return text

# --- 5. PROCESSING ---
if audio_file:
    with open("temp_file", "wb") as f:
        f.write(audio_file.getbuffer())

    if process_btn:
        with st.spinner("🤖 AI is analyzing the meeting..."):
            # A. Transcription
            result = w_model.transcribe("temp_file")
            raw_text = result["text"]
            text = clean_transcript(raw_text) # Apply Smart Cleaning

            # B. Professional Summarization
            if s_model and len(text) > 50:
                # We give the AI a clear instruction to avoid empty outputs
                summary_input = f"Summarize the key decisions and objectives: {text[:2500]}"
                summary_obj = s_model(summary_input, max_length=150, min_length=50, do_sample=False)
                summary = summary_obj[0]['summary_text']
            else:
                summary = "Meeting was too short for a detailed summary. Please see action items below."

            # C. Advanced Action Item Extraction
            lines = text.split('.')
            priority_words = ["task", "responsible", "deadline", "finish", "complete", "assign", "karna hai", "target"]
            actions = [l.strip() for l in lines if any(k in l.lower() for k in priority_words) and len(l) > 20]

            # --- 6. PROFESSIONAL UI TABS ---
            st.success("✅ Minutes of Meeting Generated")
            
            tab1, tab2, tab3 = st.tabs(["📄 Full Transcript", "📝 Executive Summary", "✅ Action Items"])

            with tab1:
                st.info("Cleaned transcript with fixed project names (Priyam, MediaPipe, etc.)")
                st.text_area("", text, height=350)

            with tab2:
                st.subheader("Meeting Overview")
                st.write(summary)
                st.markdown("---")
                # Professional MoM download format
                full_mom = f"MINUTES OF MEETING\n\nSUMMARY:\n{summary}\n\nACTION ITEMS:\n" + "\n".join([f"- {a}" for a in actions])
                st.download_button("📥 Download Official MoM", full_mom, file_name="Meeting_Minutes.txt")

            with tab3:
                st.subheader("🎯 Key Tasks & Ownership")
                if actions:
                    for i, action in enumerate(actions, 1):
                        st.markdown(f'<div class="action-card"><b>Task {i}:</b> {action}</div>', unsafe_allow_html=True)
                else:
                    st.warning("No specific tasks identified. Ensure keywords like 'Deadline' or 'Task' are used in the audio.")
else:
    st.info("👈 Upload your meeting file in the sidebar to begin.")
