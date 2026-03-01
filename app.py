import streamlit as st
import whisper
from transformers import pipeline
import os

# --- 1. PAGE CONFIG & UI STYLE ---
st.set_page_config(page_title="AI Meeting Minutes", page_icon="🎙️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .main-title { color: #1E3A8A; font-size: 40px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🎙️ AI-Powered Meeting Minutes</div>', unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Hinglish Support | Automated Summary | Action Item Extraction</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 2. SIDEBAR FOR UPLOAD ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/906/906334.png", width=100)
st.sidebar.header("Upload Meeting Audio")
audio_file = st.sidebar.file_uploader("Choose an audio file (mp3, wav)", type=["mp3", "wav", "m4a"])

st.sidebar.info("Tip: 'Small' model is faster for free hosting.")
model_size = st.sidebar.selectbox("Select Whisper Model", ["base", "small"], index=0)

# --- 3. CORE LOGIC FUNCTIONS ---
@st.cache_resource # Taaki model baar-baar load na ho
def load_models(model_size):
    st.text("Loading AI Models... Please wait.")
    whisper_model = whisper.load_model(model_size)
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    return whisper_model, summarizer

# --- 4. PROCESSING ---
if audio_file:
    # Save audio temporarily
    with open("temp_audio.mp3", "wb") as f:
        f.write(audio_file.getbuffer())
    
    if st.sidebar.button("✨ Generate Minutes of Meeting"):
        try:
            w_model, sum_model = load_models(model_size)
            
            with st.spinner("🤖 AI is listening to your recording..."):
                # Transcription
                result = w_model.transcribe("temp_audio.mp3")
                transcript = result["text"]
            
            with st.spinner("✍️ Summarizing and extracting actions..."):
                # Summarization (limiting to 3000 chars for memory)
                summary = sum_model(transcript[:3000], max_length=150, min_length=40, do_sample=False)[0]['summary_text']
                
                # Action Items Logic (Hinglish words included)
                lines = transcript.split('.')
                keywords = ["karna hai", "task", "responsible", "deadline", "action", "assignment", "decision"]
                actions = [l.strip() for l in lines if any(k in l.lower() for k in keywords)]

            # --- 5. TABS UI ---
            st.success("Analysis Complete!")
            tab1, tab2, tab3 = st.tabs(["📄 Full Transcript", "📝 Structured MoM", "✅ Action Items"])

            with tab1:
                st.text_area("Original Transcript", transcript, height=300)

            with tab2:
                st.subheader("Minutes of Meeting")
                mom_text = f"**Meeting Title:** AI Project Sync\n\n**Key Discussion Points:**\n{summary}"
                st.markdown(mom_text)
                st.download_button("📥 Download MoM", mom_text, file_name="Meeting_Minutes.txt")

            with tab3:
                st.subheader("Extracted Action Items")
                if actions:
                    for a in actions:
                        st.write(f"🔹 {a}")
                else:
                    st.write("No specific action items detected.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
else:
    st.warning("Please upload an audio file from the sidebar to start.")