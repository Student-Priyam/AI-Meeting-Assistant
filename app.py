import streamlit as st
import whisper
from transformers import pipeline
import torch

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Meeting Assistant", page_icon="🚀", layout="wide")

st.title("🎙️ AI-Powered Meeting Minutes")
st.markdown("Hinglish Support | Automated Summary | Action Item Extraction")

# --- CORE LOGIC (Stable Model Loading) ---
@st.cache_resource
def load_ai_models():
    # 1. Whisper Load
    w_model = whisper.load_model("base")
    
    # 2. Text-Generation (Using a more compatible approach)
    try:
        # device_map="auto" hatakar simple loading kar rahe hain
        s_model = pipeline(
            "text-generation", 
            model="sshleifer/distilbart-cnn-12-6"
        )
    except Exception as e:
        st.error(f"AI Loading Error: {e}")
        s_model = None
        
    return w_model, s_model

# Variables ko initialize karein taaki NameError na aaye
w_model, s_model = load_ai_models()

# --- SIDEBAR ---
st.sidebar.header("Step 1: Upload Content")
audio_file = st.sidebar.file_uploader("Upload Audio or Video", type=["mp3", "wav", "m4a", "mp4"])

if audio_file:
    # Save file temporarily
    with open("temp_file", "wb") as f:
        f.write(audio_file.getbuffer())

    if st.sidebar.button("🚀 Process Meeting Content"):
        with st.spinner("AI is analyzing (takes 2-3 mins)..."):
            # 1. Transcription
            result = w_model.transcribe("temp_file")
            text = result["text"]

            # 2. Summarization Logic (Using Text-Generation as a workaround)
            if s_model:
                prompt = f"Summarize the following meeting: {text[:2000]}"
                summary_output = s_model(prompt, max_length=150, min_length=50, do_sample=False)
                # Cleaning the output
                summary = summary_output[0]['generated_text'].replace(prompt, "").strip()
            else:
                summary = "Summary unavailable. Processing transcript only."

            # 3. Smart Action Items Extraction
            lines = text.split('.')
            act_keywords = ["task", "responsible", "karna hai", "deadline", "schedule", "assign"]
            actions = [l.strip() for l in lines if any(k in l.lower() for k in act_keywords)]

            # --- TABS UI ---
            tab1, tab2, tab3 = st.tabs(["📄 Full Transcript", "📝 Executive Summary", "✅ Action Items"])

            with tab1:
                st.text_area("Full Text", text, height=300)

            with tab2:
                st.subheader("Meeting Overview")
                st.write(summary)

            with tab3:
                st.subheader("Key Tasks & Deadlines")
                if actions:
                    for i, action in enumerate(actions, 1):
                        st.markdown(f"**{i}.** {action}")
                else:
                    st.write("No specific action items detected.")
else:
    st.info("👈 Please upload an audio or video file to start.")

