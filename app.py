import streamlit as st
import whisper
from transformers import pipeline
import os

# --- 1. PAGE SETUP & PROFESSIONAL THEME ---
st.set_page_config(page_title="AI Meeting Minutes Pro", page_icon="🎙️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff; border-radius: 4px; padding: 10px 20px; font-weight: bold;
    }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
    .status-box { padding: 20px; border-radius: 10px; background-color: #ffffff; border-left: 5px solid #ff4b4b; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# Header Section
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/906/906334.png", width=80)
with col2:
    st.title("AI-Powered Meeting Minutes")
    st.markdown("*Hinglish Support | Automated Summary | Action Item Extraction*")

st.markdown("---")

# --- 2. ROBUST MODEL LOADING ---
@st.cache_resource
def load_ai_models():
    w_model = whisper.load_model("base")
    # Smallest reliable model for summary
    try:
        s_model = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    except:
        s_model = None
    return w_model, s_model

w_model, s_model = load_ai_models()

# --- 3. SIDEBAR ---
st.sidebar.header("📁 Content Upload")
audio_file = st.sidebar.file_uploader("Upload Audio or Video", type=["mp3", "wav", "m4a", "mp4"])
process_btn = st.sidebar.button("🚀 Process Meeting Content")

# --- 4. PROCESSING LOGIC ---
if audio_file:
    with open("temp_file", "wb") as f:
        f.write(audio_file.getbuffer())

    if process_btn:
        with st.spinner("🤖 AI is analyzing the recording..."):
            # A. Transcription
            result = w_model.transcribe("temp_file")
            text = result["text"]

            # B. Professional Summarization
            if s_model and len(text) > 50:
                summary_output = s_model(text[:2500], max_length=150, min_length=40, do_sample=False)
                summary = summary_output[0]['summary_text']
            else:
                summary = "Detailed summary could not be generated. Please provide a longer recording."

            # C. Smart Action Item Extraction
            lines = text.split('.')
            act_keywords = ["task", "responsible", "karna hai", "deadline", "schedule", "assign", "finish"]
            actions = [l.strip() for l in lines if any(k in l.lower() for k in act_keywords)]

            # --- 5. DISPLAY RESULTS (PROFESSIONAL UI) ---
            st.markdown('<div class="status-box">✅ <b>Processing Complete:</b> MoM generated successfully.</div>', unsafe_allow_html=True)
            
            tab1, tab2, tab3 = st.tabs(["📄 Full Transcript", "📝 Executive Summary", "✅ Action Items"])

            with tab1:
                st.info("Raw transcript extracted from the audio.")
                st.text_area("", text, height=400)

            with tab2:
                st.subheader("Meeting Overview")
                st.write(summary)
                
                # Download Button for Professional look
                st.markdown("---")
                mom_formatted = f"MINUTES OF MEETING\n\nOVERVIEW:\n{summary}\n\nACTION ITEMS:\n" + "\n".join([f"- {a}" for a in actions])
                st.download_button("📥 Download Official MoM (TXT)", mom_formatted, file_name="Meeting_Minutes.txt")

            with tab3:
                st.subheader("Key Tasks & Deadlines")
                if actions:
                    for i, action in enumerate(actions, 1):
                        st.markdown(f"**{i}.** {action}")
                else:
                    st.warning("No clear action items detected in the discussion.")
else:
    st.info("👈 Please upload a recording in the sidebar to generate meeting minutes.")
