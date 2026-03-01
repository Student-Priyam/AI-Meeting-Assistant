import streamlit as st
import whisper
from transformers import pipeline
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Meeting Pro", page_icon="🚀", layout="wide")

# Custom UI for Professional Look
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stTable { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ Next-Gen AI Meeting Assistant")
st.info("Supported Formats: MP3, WAV, M4A, MP4 (Video)")

# --- SIDEBAR ---
st.sidebar.header("Step 1: Upload Content")
# Added mp4 and mkv support here
audio_file = st.sidebar.file_uploader("Upload Audio or Video", type=["mp3", "wav", "m4a", "mp4", "mkv"])

# --- CORE LOGIC ---
@st.cache_resource
def load_ai_models():
    w_model = whisper.load_model("base")
    s_model = pipeline("summarization", model="facebook/bart-large-cnn")
    return w_model, s_model

if audio_file:
    with open("temp_file", "wb") as f:
        f.write(audio_file.getbuffer())

    if st.sidebar.button("🚀 Process Meeting Content"):
        w_model, s_model = load_ai_models()
        
        with st.spinner("AI is analyzing your content..."):
            # 1. Transcription
            result = w_model.transcribe("temp_file")
            text = result["text"]

            # 2. Advanced Summary
            summary = s_model(text[:2500], max_length=150, min_length=50)[0]['summary_text']

            # 3. Smart Extraction
            lines = text.split('.')
            act_keywords = ["task", "responsible", "karna hai", "deadline", "schedule", "meeting"]
            actions = [l.strip() for l in lines if any(k in l.lower() for k in act_keywords)]

        # --- HIGH LEVEL UI TABS ---
        tab1, tab2, tab3 = st.tabs(["📄 Transcript", "📝 Executive Summary", "✅ Action Plan"])

        with tab1:
            st.text_area("Raw Text", text, height=300)

        with tab2:
            st.subheader("Meeting Overview")
            st.write(summary)
            st.download_button("Download Summary", summary, file_name="Summary.txt")

        with tab3:
            st.subheader("Task Assignments")
            if actions:
                # Displaying actions in a professional list
                for i, action in enumerate(actions):
                    st.markdown(f"**{i+1}.** {action}")
            else:
                st.write("No specific actions detected. Try a longer recording!")

else:
    st.warning("Please upload a file to begin.")
