import streamlit as st
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import re

# --- 1. ENTERPRISE UI SETUP ---
st.set_page_config(page_title="Enterprise Meeting Intelligence", page_icon="💼", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .report-card { 
        padding: 20px; border-radius: 12px; background-color: white; 
        border-left: 8px solid #004a99; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .metric-text { color: #004a99; font-weight: bold; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)

st.title("💼 Enterprise Meeting Intelligence")
st.markdown("Automated Transcription, Strategic Insights, and Deliverable Tracking")

# --- 2. HIGH-LEVEL LOGIC (Industry Neutral) ---
def get_high_level_actions(text):
    """Semantic logic to extract only high-intent commitments."""
    lines = text.split('.')
    deliverables = []
    
    # Intent Patterns: [Actor] + [Commitment] + [Action]
    intent_patterns = [
        r"(i|we|team|everyone)\s+(will|need to|must|should|going to|tasked to)",
        r"(deadline|finish|complete|finalize|integrate|develop|send|update)",
        r"(by|on|before)\s+(friday|monday|tomorrow|next week|weekend|[0-9]+)"
    ]
    
    for line in lines:
        clean_l = line.strip()
        if len(clean_l) > 35:
            if any(re.search(p, clean_l.lower()) for p in intent_patterns):
                # Universal filter for filler sentences
                if not any(f in clean_l.lower() for f in ["there are", "this is", "hello"]):
                    deliverables.append(clean_l)
    return deliverables

# --- 3. PRO MODEL LOADING ---
@st.cache_resource
def load_enterprise_models():
    # Whisper for Transcription
    w_model = whisper.load_model("base")
    
    # Direct Model Loading for Summarization (Professional Standard)
    model_name = "sshleifer/distilbart-cnn-12-6"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    s_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    
    return w_model, tokenizer, s_model

# Handle potential loading errors gracefully for the UI
try:
    w_model, tokenizer, s_model = load_enterprise_models()
except Exception as e:
    st.error(f"Initialization Error: {e}. Please check your requirements.txt")

# --- 4. INPUT SECTION ---
st.sidebar.header("📥 Input Source")
audio_file = st.sidebar.file_uploader("Upload Meeting (Audio/Video)", type=["mp3", "wav", "m4a", "mp4"])
meeting_domain = st.sidebar.selectbox("Meeting Domain", ["Technical", "Sales/Marketing", "Management", "General"])

# --- 5. EXECUTION ENGINE ---
if audio_file:
    with open("temp_file", "wb") as f:
        f.write(audio_file.getbuffer())

    if st.sidebar.button("🚀 Analyze Meeting"):
        with st.spinner("Synthesizing meeting data..."):
            # A. Transcription
            result = w_model.transcribe("temp_file")
            raw_text = result["text"]

            # B. High-Level Action Extraction
            deliverables = get_high_level_actions(raw_text)
            
            # C. Strategic Summarization (Direct Inference)
            inputs = tokenizer("summarize: " + raw_text[:2000], return_tensors="pt", max_length=1024, truncation=True)
            summary_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=50, length_penalty=2.0, num_beams=4, early_stopping=True)
            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

            # --- 6. CLIENT-READY TABS ---
            tab1, tab2, tab3 = st.tabs(["📄 Detailed Records", "📝 Executive Insights", "🎯 Strategic Deliverables"])

            with tab1:
                st.subheader("Comprehensive Meeting Record")
                st.text_area("", raw_text, height=400)

            with tab2:
                st.subheader("Executive Briefing")
                st.markdown(f"<span class='metric-text'>Domain:</span> {meeting_domain}", unsafe_allow_html=True)
                st.write(summary)
                
                report = f"EXECUTIVE SUMMARY ({meeting_domain})\n\nDECISIONS:\n{summary}\n\nDELIVERABLES:\n" + "\n".join([f"- {d}" for d in deliverables])
                st.download_button("📥 Export Meeting Report", report, file_name="Enterprise_MoM.txt")

            with tab3:
                st.subheader("Key Outcomes & Accountability")
                if deliverables:
                    for i, d in enumerate(deliverables, 1):
                        st.markdown(f'<div class="report-card"><div class="metric-text">Deliverable {i}</div>{d}</div>', unsafe_allow_html=True)
                else:
                    st.warning("No high-intent deliverables identified.")
else:
    st.info("👈 Please upload your meeting recording to begin.")
