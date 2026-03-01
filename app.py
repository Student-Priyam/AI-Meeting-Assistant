import streamlit as st
import whisper
from transformers import pipeline
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

# --- 2. UNIVERSAL LOGIC FUNCTIONS ---
def get_high_level_actions(text):
    """Semantic logic to extract only high-intent commitments."""
    lines = text.split('.')
    deliverables = []
    
    # Universal Action Patterns (NLP-lite approach)
    # Looking for: [Actor] + [Commitment Word] + [Action]
    intent_patterns = [
        r"(i|we|team|everyone)\s+(will|need to|must|should|going to|tasked to)",
        r"(deadline|finish|complete|finalize|integrate|develop|send|update)",
        r"(by|on|before)\s+(friday|monday|tomorrow|next week|weekend|[0-9]+)"
    ]
    
    for line in lines:
        clean_l = line.strip()
        # High-level check: Line must be substantial and match intent
        if len(clean_l) > 40:
            match_score = sum(1 for p in intent_patterns if re.search(p, clean_l.lower()))
            if match_score >= 1: # Only pick lines with clear intent
                deliverables.append(clean_l)
    return deliverables

# --- 3. MODELS ---
@st.cache_resource
def load_enterprise_models():
    w_model = whisper.load_model("base")
    s_model = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    return w_model, s_model

w_model, s_model = load_enterprise_models()

# --- 4. INPUT SECTION ---
st.sidebar.header("📥 Input Source")
audio_file = st.sidebar.file_uploader("Upload Meeting (Audio/Video)", type=["mp3", "wav", "m4a", "mp4"])
meeting_domain = st.sidebar.selectbox("Meeting Domain", ["Technical", "Sales/Marketing", "Management", "General"])
user_keywords = st.sidebar.text_input("Critical Terms (e.g. MediaPipe, Budget)")

# --- 5. EXECUTION ENGINE ---
if audio_file:
    with open("temp_file", "wb") as f:
        f.write(audio_file.getbuffer())

    if st.sidebar.button("🚀 Analyze Meeting"):
        with st.spinner("Synthesizing meeting data..."):
            # A. Transcription
            result = w_model.transcribe("temp_file")
            raw_text = result["text"]

            # B. High-Level Logic Processing
            deliverables = get_high_level_actions(raw_text)
            
            # C. Strategic Summarization
            summary_prompt = f"Identify core decisions in this {meeting_domain} meeting: {raw_text[:2000]}"
            summary_obj = s_model(summary_prompt, max_length=150, min_length=60, do_sample=False)
            summary = summary_obj[0]['summary_text']

            # --- 6. CLIENT-READY TABS ---
            tab1, tab2, tab3 = st.tabs(["📄 Detailed Records", "📝 Executive Insights", "🎯 Strategic Deliverables"])

            with tab1:
                st.subheader("Comprehensive Meeting Transcript")
                st.text_area("", raw_text, height=400)

            with tab2:
                st.subheader("Executive Briefing")
                st.markdown(f"<span class='metric-text'>Domain:</span> {meeting_domain}", unsafe_allow_html=True)
                st.write(summary)
                
                # Report Export Logic
                report = f"EXECUTIVE SUMMARY ({meeting_domain})\n\nDECISIONS:\n{summary}\n\nDELIVERABLES:\n" + "\n".join([f"- {d}" for d in deliverables])
                st.download_button("📥 Export Meeting Report", report, file_name="Enterprise_MoM.txt")

            with tab3:
                st.subheader("Key Outcomes & Accountability")
                if deliverables:
                    for i, d in enumerate(deliverables, 1):
                        st.markdown(f'<div class="report-card"><div class="metric-text">Outcome {i}</div>{d}</div>', unsafe_allow_html=True)
                else:
                    st.warning("No high-intent deliverables identified. Try adjusting the input recording.")
else:
    st.info("👈 Upload your meeting recording to begin professional synthesis.")

