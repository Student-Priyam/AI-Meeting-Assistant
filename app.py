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

# --- 2. HIGH-LEVEL ANALYTICS LOGIC (Universal) ---
def extract_strategic_outcomes(text):
    """Semantic logic to identify future commitments and key decisions."""
    lines = text.split('.')
    deliverables = []
    
    # Intent Patterns: [Subject] + [Commitment] + [Action Verb]
    intent_patterns = [
        r"(i|we|team|everyone|dept)\s+(will|must|should|need to|tasked to|going to)",
        r"(complete|finalize|integrate|develop|send|update|post|push|optimize|verify|check|design)",
        r"(by|on|before|deadline|target)\s+(friday|monday|next week|tomorrow|end of day|[0-9]+)"
    ]
    
    for line in lines:
        clean_l = line.strip()
        if len(clean_l) > 35:
            match_score = sum(1 for p in intent_patterns if re.search(p, clean_l.lower()))
            if match_score >= 1:
                # Filter out universal meeting fillers
                fillers = ["there are", "hello", "i am", "today is", "welcome", "we are a"]
                if not any(f in clean_l.lower() for f in fillers):
                    deliverables.append(clean_l)
    return deliverables

# --- 3. PRO MODEL ARCHITECTURE ---
@st.cache_resource
def load_enterprise_engine():
    w_model = whisper.load_model("base")
    model_name = "sshleifer/distilbart-cnn-12-6"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    s_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return w_model, tokenizer, s_model

try:
    w_model, tokenizer, s_model = load_enterprise_engine()
except Exception as e:
    st.error(f"Engine Initialization Error: {e}")

# --- 4. INPUT SECTION (AUDIO & VIDEO) ---
st.sidebar.header("📁 Input Source")
# Supporting all common formats
uploaded_file = st.sidebar.file_uploader("Upload Meeting (Audio or Video)", 
                                        type=["mp3", "wav", "m4a", "mp4", "mkv", "mov"])
industry_context = st.sidebar.selectbox("Industry Domain", 
                                        ["Technology", "Corporate Strategy", "Operations", "Sales & Marketing", "General Management"])

# --- 5. SYNTHESIS ENGINE ---
if uploaded_file:
    # Save temp file for processing
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # UI Preview
    if uploaded_file.type.startswith('video'):
        st.subheader("📺 Video Content Preview")
        st.video(uploaded_file)
    else:
        st.subheader("🔊 Audio Content Preview")
        st.audio(uploaded_file)

    if st.sidebar.button("🚀 Analyze & Generate Intelligence"):
        with st.spinner("AI is synthesizing strategic data..."):
            # A. Transcription (Whisper handles video tracks natively)
            result = w_model.transcribe(temp_path)
            raw_text = result["text"]

            # B. Smart Outcome Extraction
            outcomes = extract_strategic_outcomes(raw_text)
            
            # C. Executive Summarization
            inputs = tokenizer(f"Summarize key decisions in this {industry_context} meeting: " + raw_text[:2000], 
                               return_tensors="pt", max_length=1024, truncation=True)
            summary_ids = s_model.generate(inputs["input_ids"], max_length=150, min_length=60, length_penalty=2.0)
            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

            # --- 6. PRESENTATION LAYER (CLIENT-READY) ---
            tab1, tab2, tab3 = st.tabs(["📄 Detailed Records", "📝 Executive Insights", "🎯 Strategic Deliverables"])

            with tab1:
                st.subheader("Comprehensive Meeting Records")
                st.text_area("", raw_text, height=400)

            with tab2:
                st.subheader("Executive Insights")
                st.markdown(f"**Strategic Focus:** {industry_context}")
                st.write(summary)
                
                report_text = f"EXECUTIVE SUMMARY ({industry_context})\n\nDECISIONS:\n{summary}\n\nSTRATEGIC DELIVERABLES:\n" + "\n".join([f"- {o}" for o in outcomes])
                st.download_button("📥 Export Professional Report", report_text, file_name="Executive_MoM.txt")

            with tab3:
                st.subheader("Deliverables & Accountability Tracking")
                if outcomes:
                    for i, outcome in enumerate(outcomes, 1):
                        st.markdown(f'<div class="report-card"><div class="metric-title">Outcome {i}</div>{outcome}</div>', unsafe_allow_html=True)
                else:
                    st.warning("No high-intent deliverables identified. System filtered generic statements.")
    
    # Cleanup temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)
else:
    st.info("👈 Please upload a meeting recording to begin professional synthesis.")
