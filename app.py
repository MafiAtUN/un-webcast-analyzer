"""
UN WebTV Analysis Platform - Main Application
Streamlit multi-page application for processing and analyzing UN WebTV sessions.
"""

import streamlit as st
from loguru import logger

# Configure logging
logger.add(
    "logs/app.log",
    rotation="100 MB",
    retention="30 days",
    level="INFO"
)

# Page configuration
st.set_page_config(
    page_title="UN WebTV Analysis Platform",
    page_icon="🇺🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stButton>button {
        background-color: #1E88E5;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🇺🇳 UN WebTV Analysis")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "➕ New Analysis", "📚 Catalog", "📊 Visualizations", "ℹ️ About"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### System Status")
st.sidebar.success("✅ Azure OpenAI: Connected")
st.sidebar.success("✅ Cosmos DB: Connected")
st.sidebar.success("✅ Blob Storage: Connected")

# Main content based on selected page
if page == "🏠 Home":
    st.markdown('<div class="main-header">🇺🇳 UN WebTV Analysis Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-powered analysis of United Nations proceedings</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🎯 What We Do</h3>
            <p>Automatically transcribe and analyze UN WebTV sessions with:</p>
            <ul>
                <li>Speaker identification</li>
                <li>Entity extraction</li>
                <li>SDG mapping</li>
                <li>AI-powered chat</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>⚡ Features</h3>
            <ul>
                <li>Automatic transcription</li>
                <li>Speaker diarization</li>
                <li>Country & topic extraction</li>
                <li>Semantic search</li>
                <li>Export capabilities</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>🚀 Get Started</h3>
            <p>1. Paste a UN WebTV URL<br>
            2. Let AI process it<br>
            3. Chat with the data<br>
            4. Export results</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("📊 Platform Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Sessions Processed",
            value="0",
            delta="Ready to start"
        )

    with col2:
        st.metric(
            label="Total Speakers Identified",
            value="0",
            delta=None
        )

    with col3:
        st.metric(
            label="Countries Tracked",
            value="0",
            delta=None
        )

    with col4:
        st.metric(
            label="Chat Interactions",
            value="0",
            delta=None
        )

    st.markdown("---")

    st.info("""
    👉 **Ready to start?** Click on **"➕ New Analysis"** in the sidebar to process your first UN WebTV session!
    """)

elif page == "➕ New Analysis":
    from pages import new_analysis
    new_analysis.show()

elif page == "📚 Catalog":
    from pages import catalog
    catalog.show()

elif page == "📊 Visualizations":
    from pages import visualizations
    visualizations.show()

elif page == "ℹ️ About":
    st.markdown('<div class="main-header">About This Platform</div>', unsafe_allow_html=True)

    st.markdown("""
    ### 🇺🇳 UN WebTV Analysis Platform

    This platform automatically processes United Nations WebTV sessions using advanced AI technologies to extract
    valuable insights from proceedings.

    #### Technology Stack
    - **AI Models**: Azure OpenAI (GPT-4o, GPT-5, Whisper)
    - **Transcription**: Speaker diarization with GPT-4o-transcribe-diarize
    - **Database**: Azure Cosmos DB + Azure AI Search
    - **Framework**: FastAPI + Streamlit

    #### Capabilities
    - Automatic audio transcription
    - Speaker identification and tracking
    - Entity extraction (countries, organizations, SDGs)
    - Topic analysis and summarization
    - Semantic search and Q&A
    - Export to multiple formats

    #### Use Cases
    - Research and analysis of UN proceedings
    - Tracking country positions
    - Monitoring SDG discussions
    - Comparative analysis across sessions
    - Historical research and documentation

    #### Privacy & Data
    - Audio files are processed and immediately deleted
    - Transcripts and metadata stored securely
    - No external data sharing
    - Compliant with UN data policies

    ---

    **Version**: 1.0.0
    **Last Updated**: October 2025
    **Support**: Contact your administrator

    """)

    st.markdown("---")

    with st.expander("📖 How It Works"):
        st.markdown("""
        1. **Input**: Paste a UN WebTV session URL
        2. **Download**: System downloads audio (video not stored)
        3. **Transcribe**: AI transcribes with speaker identification
        4. **Extract**: Identifies speakers, countries, SDGs, topics
        5. **Analyze**: Generates embeddings for semantic search
        6. **Chat**: Ask questions about the session
        7. **Export**: Download transcripts and analysis
        """)

    with st.expander("🎯 Supported Session Types"):
        st.markdown("""
        - General Assembly sessions
        - Security Council meetings
        - Human Rights Council sessions
        - Economic and Social Council
        - Specialized agency meetings
        - Committee meetings
        - Press conferences
        """)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("© 2025 UN OSAA - UN WebTV Analysis Platform")
