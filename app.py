import streamlit as st
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import re
import os

# --- 1. ENTERPRISE UI & UX CONFIG ---
st.set_page_config(page_title="Pro Meeting Intelligence", page_icon="💼", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .report-card { 
        padding: 24px; border-radius: 12px; background-color: white; 
        border-left: 8px solid #1e40af; margin-bottom: 20px; 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .metric-title { color: #1e40af; font-weight: 700; font-size: 1.2em; margin-bottom: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] {
        background-color: white; border-radius: 6px; padding: 12px 28px; border: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💼 Enterprise Meeting Intelligence")
st.markdown("Universal Audio & Video Synthesis • Strategic Insights • Deliverable Tracking")
st.markdown("---")

# --- 2. UNIVERSAL SEMANTIC LOGIC (Industry Neutral) ---
def extract_strategic_outcomes(text):
    """Grammar-based logic to extract high-intent commitments."""
    lines = text.split('.')
    deliverables = []
    
    # Universal Intent Patterns: [Subject] + [Commitment] + [Action Verb]
    intent_patterns = [
        r"(i|we|team|everyone|dept|management)\s+(will|must|should|need to|tasked to|going to)",
        r"(complete|finalize|integrate|develop|send|update|post|push|optimize|verify|check|design)",
        r"(by|on|before|deadline|target|schedule)\s+(friday|monday|next week|tomorrow|end of day|[0-9]+)"
    ]
    
    for line in lines:
        clean_l = line.strip()
        if len(clean_l) > 38: # Minimum length for a professional sentence
            # Checking for professional intent patterns
            match_score = sum(1 for p in intent_patterns if re.search(p, clean_l.lower()))
            if match_score >= 1:
                # Filter out generic introductory/filler phrases
                fillers = ["there are", "hello", "i am", "today is", "welcome", "we are a"]
                if not any(f in clean_l.lower() for f in fillers):
                    deliverables.append(clean_l)
    return deliverables

# --- 3. PRO MODEL ARCHITECTURE (Optimized & Stable) ---
@st.cache_resource
def load_enterprise_engine():
    # Whisper for robust transcription
    w_model = whisper.load_model("base")
    
    # Direct Model Loading to avoid 'Unknown Task' errors
    model_name = "sshleifer/distilbart-cnn-12-6"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    s_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    
    return w_model, tokenizer, s_model

try:
    w_model, tokenizer, s_model = load_enterprise_engine()
except Exception as e:
    st.error(f"Engine Initialization Error: {e}. Please check requirements.txt")

# --- 4. INPUT SECTION (AUDIO & VIDEO) ---
st.sidebar.header("📁 Input Source")
uploaded_file = st.sidebar.file_uploader("Upload Recording", 
                                        type=["mp3", "wav", "m4a", "mp4", "mkv", "mov"])
industry_context = st.sidebar.selectbox("Industry Domain", 
                                        ["Technology", "Corporate Strategy", "Operations", "Sales & Marketing", "General Management"])

# --- 5. SYNTHESIS ENGINE ---
if uploaded_file:
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Professional Player Preview
    if uploaded_file.type.startswith('video'):
        st.subheader("📺 Content Preview")
        st.video(uploaded_file)
    else:
        st.subheader("🔊 Content Preview")
        st.audio(uploaded_file)

    if st.sidebar.button("🚀 Analyze & Generate Intelligence"):
        with st.spinner("AI is synthesizing strategic data..."):
            # A. Transcription (Whisper handles video natively)
            result = w_model.transcribe(temp_path)
            raw_text = result["text"]

            # B. Smart Deliverable Extraction
            outcomes = extract_strategic_outcomes(raw_text)
            
            # C. Executive Summarization (Fixing 'forced_bos_token_id' warning)
            inputs = tokenizer(f"Summarize key decisions in this {industry_context} meeting: " + raw_text[:2000], 
                               return_tensors="pt", max_length=1024, truncation=True)
            
            summary_ids = s_model.generate(
                inputs["input_ids"], 
                max_length=150, 
                min_length=60, 
                length_penalty=2.0,
                forced_bos_token_id=0 # Warning fix
            )
            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

            # --- 6. PRESENTATION LAYER (CLIENT-READY) ---
            tab1, tab2, tab3 = st.tabs(["📄 Detailed Records", "📝 Executive Insights", "🎯 Strategic Deliverables"])

            with tab1:
                st.subheader("Comprehensive Meeting Record")
                st.text_area("", raw_text, height=400)

            with tab2:
                st.subheader("Executive Briefing")
                st.markdown(f"**Strategic Focus:** {industry_context}")
                st.info(summary)
                
                # Formal Report Download
                report_text = f"EXECUTIVE SUMMARY ({industry_context})\n\nDECISIONS:\n{summary}\n\nSTRATEGIC DELIVERABLES:\n" + "\n".join([f"- {o}" for o in outcomes])
                st.markdown("---")
                st.download_button("📥 Export Meeting Report", report_text, file_name="Executive_MoM.txt")

            with tab3:
                st.subheader("Key Outcomes & Accountability")
                if outcomes:
                    for i, outcome in enumerate(outcomes, 1):
                        st.markdown(f'<div class="report-card"><div class="metric-title">Outcome {i}</div>{outcome}</div>', unsafe_allow_html=True)
                else:
                    st.warning("No high-intent deliverables identified. Generic filler sentences were automatically filtered.")
    
    # Clean up
    if os.path.exists(temp_path):
        os.remove(temp_path)
else:
    st.info("👈 Please upload a meeting recording (Audio or Video) to begin synthesis.")
