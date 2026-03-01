import streamlit as st
import whisper
from transformers import pipeline
import os

# --- 1. PRO UI SETUP ---
st.set_page_config(page_title="Pro Meeting AI", page_icon="💼", layout="wide")

# Custom CSS for a Corporate Look
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: white; border-radius: 8px; padding: 12px 25px; border: 1px solid #ddd;
    }
    .task-box { 
        padding: 20px; border-radius: 12px; background-color: white; 
        border-left: 8px solid #007bff; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💼 Enterprise Meeting Intelligence")
st.markdown("Automated Minutes, Task Extraction, and Actionable Insights")

# --- 2. SIDEBAR (Client Customization) ---
st.sidebar.header("📁 Meeting Configuration")
audio_file = st.sidebar.file_uploader("Upload Recording", type=["mp3", "wav", "m4a", "mp4"])

# Client Input: Meeting Context
meeting_context = st.sidebar.text_input("Meeting Context (Optional)", placeholder="e.g. Project Sync, Sales Pitch, UI Review")
custom_keywords = st.sidebar.text_area("Key Terms to Track", placeholder="e.g. MediaPipe, Deadline, Budget, Priyam")

# --- 3. MODEL LOADING ---
@st.cache_resource
def load_pro_models():
    w_model = whisper.load_model("base")
    # Using a robust summarizer
    try:
        s_model = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    except:
        s_model = None
    return w_model, s_model

w_model, s_model = load_pro_models()

# --- 4. SMART ANALYZER LOGIC ---
def analyze_meeting(text, context, keywords):
    # Professional Logic: Filter based on Intent, not just words
    lines = text.split('.')
    action_items = []
    
    # Intent-based keywords (Universal)
    intent_words = ["will", "decided", "assign", "complete", "responsible", "deadline", "by next", "karna hai"]
    if keywords:
        intent_words.extend([k.strip().lower() for k in keywords.split(',')])

    for line in lines:
        clean_l = line.strip()
        # Quality Check: Sentence length and Intent presence
        if len(clean_l) > 30:
            if any(word in clean_l.lower() for word in intent_words):
                action_items.append(clean_l)
                
    return action_items

# --- 5. EXECUTION ---
if audio_file:
    with open("temp_file", "wb") as f:
        f.write(audio_file.getbuffer())

    if st.sidebar.button("🚀 Run Analysis"):
        with st.spinner("🤖 AI is synthesizing meeting data..."):
            # A. Transcription
            result = w_model.transcribe("temp_file")
            text = result["text"]

            # B. Smart Filtering
            final_actions = analyze_meeting(text, meeting_context, custom_keywords)

            # C. Executive Summary
            summary_prompt = f"Topic: {meeting_context}. Summarize decisions: {text[:2000]}"
            summary_obj = s_model(summary_prompt, max_length=150, min_length=60, do_sample=False)
            summary = summary_obj[0]['summary_text']

            # --- 6. CLIENT PRESENTATION TABS ---
            tab1, tab2, tab3 = st.tabs(["📄 Full Transcript", "📝 Executive Summary", "✅ Action Items"])

            with tab1:
                st.text_area("Original Content", text, height=400)

            with tab2:
                st.subheader("Executive Overview")
                st.markdown(f"> **Context:** {meeting_context if meeting_context else 'General Meeting'}")
                st.write(summary)
                
                # Professional Download Content
                report = f"EXECUTIVE SUMMARY:\n{summary}\n\nACTION ITEMS:\n" + "\n".join([f"- {a}" for a in final_actions])
                st.download_button("📥 Export Professional Report", report, file_name="Meeting_Report.txt")

            with tab3:
                st.subheader("🎯 Verified Deliverables")
                if final_actions:
                    for i, item in enumerate(final_actions, 1):
                        st.markdown(f'<div class="task-box"><b>Deliverable {i}:</b><br>{item}</div>', unsafe_allow_html=True)
                else:
                    st.warning("No high-intent action items found. Adjust keywords in the sidebar if needed.")
else:
    st.info("Please upload a meeting recording to generate professional insights.")
