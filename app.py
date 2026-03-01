import streamlit as st
import whisper
from transformers import pipeline
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Meeting Pro", page_icon="🚀", layout="wide")

st.title("🎙️ Next-Gen AI Meeting Assistant")

# --- CORE LOGIC (Lightweight & Stable) ---
@st.cache_resource
def load_ai_models():
    # Whisper load karna (Base model is safe for RAM)
    w_model = whisper.load_model("base")
    
    # BART ki jagah DistilBART (Smaller & Faster) use karein
    try:
        s_model = pipeline(
            "summarization", 
            model="sshleifer/distilbart-cnn-12-6",
            device_map="auto"
        )
    except Exception as e:
        st.error(f"Summarizer Loading Error: {e}")
        s_model = None
        
    return w_model, s_model

# Initialize variables to avoid NameError
w_model, s_model = load_ai_models()

# --- SIDEBAR ---
st.sidebar.header("Step 1: Upload Content")
audio_file = st.sidebar.file_uploader("Upload Audio or Video", type=["mp3", "wav", "m4a", "mp4"])

if audio_file:
    with open("temp_file", "wb") as f:
        f.write(audio_file.getbuffer())

    if st.sidebar.button("🚀 Process Meeting Content"):
        with st.spinner("AI is analyzing (this takes 2-3 mins)..."):
            # 1. Transcription
            result = w_model.transcribe("temp_file")
            text = result["text"]

            # 2. Summarization Logic
            if s_model:
                summary_output = s_model(text[:2000], max_length=150, min_length=50, do_sample=False)
                summary = summary_output[0]['summary_text']
            else:
                summary = "Summary unavailable (Model Load Error). Check logs."

            # 3. Action Items Extraction
            lines = text.split('.')
            act_keywords = ["task", "responsible", "karna hai", "deadline", "schedule"]
            actions = [l.strip() for l in lines if any(k in l.lower() for k in act_keywords)]

            # --- TABS UI ---
            tab1, tab2, tab3 = st.tabs(["📄 Transcript", "📝 Summary", "✅ Actions"])
            with tab1: st.text_area("Transcript", text, height=300)
            with tab2: st.write(summary)
            with tab3:
                for i, action in enumerate(actions, 1):
                    st.markdown(f"**{i}.** {action}")
else:
    st.info("👈 Upload your MP4/MP3 file to start.")
