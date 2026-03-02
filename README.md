# AI-Meeting-Assistant

# The Problem Statement

**Information Overload**: In professional and academic settings, 55–60 minute sessions are common, but rewatching them to find one specific detail (like a task assigned to "Rahul") is a massive waste of human productivity.

**Manual Inefficiency**: Traditional note-taking is prone to human error, often missing "Who-to-Whom" task assignments or specific deadlines mentioned in passing.

# Tech Stack

**Frontend**: Streamlit (SaaS-style Responsive UI).

**Speech-to-Text**: OpenAI Whisper (Base) for robust multi-lingual transcription.

**Summarization**: BART (DistilBART-CNN-12-6) for high-compression executive summaries.

**Database**: SQLite3 for persistent meeting archives and historical retrieval.

**Audio Engine**: Pydub + FFmpeg for professional-grade audio manipulation.

**Backend**: Python 3.13 with audioop-lts for modern system compatibility.

# Technical Implementation

**Memory-Safe Audio Chunking**
To prevent the system from crashing on a 55-minute file, the engine implements a sliding window chunking logic. It slices the audio into 5-minute segments, processes them individually to keep RAM usage low, and merges the results into a single coherent transcript.

**Adaptive Workspace Intelligence**
The platform uses conditional NLP patterns to pivot its focus based on the user's selection:

Corporate Mode: Prioritizes verbs and nouns related to "deadlines," "decisions," and "accountability".

Academic Mode: Prioritizes "core concepts," "homework assignments," and "exam prep".

**Pinpoint Strategic Query Engine**
Instead of searching through a generic summary, the query engine splits the full transcript into sentence-level entities. When a user asks about "Rahul's role," the AI performs a keyword-weighted scan to jump past the meeting introduction and find the exact sentence where that person was mentioned.

# Performance Benchmarks

**Transcription Speed**: ~8–12 minutes for a 55-minute session on CPU (Standard Tier).

**Inference Latency**: Executive summaries are generated in <180 seconds for large-scale transcripts.

**Memory Efficiency**: Chunking logic reduces peak RAM usage from 4GB+ to under 1.2GB, allowing deployment on low-resource environments.

# Future Roadmap

**Speaker Diarization**: Implementing logic to identify different voices (e.g., distinguishing between "Rahul" and the "Manager").

**Sentiment Analysis**: Detecting the "tone" of the meeting to highlight moments of conflict or consensus.

**Calendar Integration**: Automatically pushing "Action Items" to Google Calendar or Microsoft Teams.

## 🌐 Live Demo
You can access the live application here: 
[On Streamlit Cloud] : https://ai-meeting-assistant-2222.streamlit.app/


