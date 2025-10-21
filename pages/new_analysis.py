"""
New Analysis Page
Allows users to submit UN WebTV URLs for processing.
"""

import streamlit as st
import asyncio
from loguru import logger


def show():
    """Display the new analysis page."""
    st.title("➕ New Session Analysis")

    st.markdown("""
    Submit a UN WebTV session URL for automated analysis. The system will:
    - Download and transcribe the audio
    - Identify speakers and extract entities
    - Generate embeddings for semantic search
    - Create an executive summary
    """)

    st.markdown("---")

    # Input form
    with st.form("session_form"):
        url = st.text_input(
            "UN WebTV Session URL",
            placeholder="https://webtv.un.org/en/asset/k1b/k1baa85czq",
            help="Paste the full URL of the UN WebTV session you want to analyze"
        )

        col1, col2 = st.columns([1, 4])

        with col1:
            submit = st.form_submit_button("🚀 Process Session", use_container_width=True)

    if submit:
        if not url:
            st.error("❌ Please enter a UN WebTV URL")
        elif "webtv.un.org" not in url:
            st.error("❌ Please enter a valid UN WebTV URL (must contain 'webtv.un.org')")
        else:
            process_session(url)


def process_session(url: str):
    """
    Process a UN WebTV session.

    Args:
        url: UN WebTV session URL
    """
    from backend.services.session_processor import session_processor
    from backend.services.database import db_service

    # Create progress container
    progress_container = st.container()

    with progress_container:
        st.info(f"🎬 Processing session: {url}")

        # Initialize database
        with st.spinner("Initializing database connection..."):
            try:
                # Run async initialization
                asyncio.run(db_service.initialize())
                st.success("✅ Database connected")
            except Exception as e:
                st.error(f"❌ Failed to initialize database: {str(e)}")
                logger.error(f"Database initialization failed: {str(e)}")
                return

        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Simulate progress updates (in real implementation, use WebSocket)
            status_text.text("📥 Downloading session metadata...")
            progress_bar.progress(10)

            status_text.text("🎵 Downloading audio...")
            progress_bar.progress(20)

            status_text.text("🎤 Transcribing with speaker identification...")
            progress_bar.progress(40)

            status_text.text("🔍 Extracting entities (speakers, countries, SDGs)...")
            progress_bar.progress(60)

            status_text.text("📝 Generating summary...")
            progress_bar.progress(75)

            status_text.text("🧮 Creating embeddings...")
            progress_bar.progress(85)

            # Process session
            status_text.text("⚙️ Processing session...")
            session = asyncio.run(session_processor.process_session(url))

            if session:
                progress_bar.progress(100)
                status_text.text("✅ Processing complete!")

                # Show results
                st.success("🎉 Session processed successfully!")

                # Display session info
                st.markdown("### 📊 Session Information")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Session ID", session.id)
                    st.metric("Duration", f"{session.duration_seconds // 60} min")

                with col2:
                    st.metric("Date", session.date.strftime("%Y-%m-%d") if session.date else "N/A")
                    st.metric("Location", session.location or "N/A")

                with col3:
                    st.metric("Languages", ", ".join(session.languages))
                    st.metric("Processing Status", session.processing_status.upper())

                # Display title and summary
                st.markdown("### 📝 Session Details")
                st.write(f"**Title:** {session.title}")

                if session.summary:
                    st.write(f"**Summary:** {session.summary}")

                # Display entities if available
                if session.entities:
                    st.markdown("### 🏷️ Extracted Entities")

                    tab1, tab2, tab3, tab4 = st.tabs(["Countries", "Speakers", "SDGs", "Topics"])

                    with tab1:
                        if session.entities.countries:
                            st.write(", ".join(session.entities.countries))
                        else:
                            st.info("No countries extracted yet")

                    with tab2:
                        if session.entities.speakers:
                            for speaker in session.entities.speakers:
                                st.write(f"- **{speaker.name}** ({speaker.country or 'N/A'})")
                        else:
                            st.info("No speakers extracted yet")

                    with tab3:
                        if session.entities.sdgs:
                            for sdg in session.entities.sdgs:
                                st.write(f"- **SDG {sdg.number}**: {sdg.name}")
                        else:
                            st.info("No SDGs extracted yet")

                    with tab4:
                        if session.entities.topics:
                            st.write(", ".join(session.entities.topics))
                        else:
                            st.info("No topics extracted yet")

                # Action buttons
                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("💬 Chat with this Session", use_container_width=True):
                        st.session_state.current_session_id = session.id
                        st.session_state.page = "💬 Chat"
                        st.rerun()

                with col2:
                    if st.button("📚 View in Catalog", use_container_width=True):
                        st.session_state.page = "📚 Catalog"
                        st.rerun()

            else:
                progress_bar.progress(0)
                status_text.text("")
                st.error("❌ Session processing failed. Please check the logs for details.")

        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.error(f"❌ An error occurred: {str(e)}")
            logger.error(f"Session processing error: {str(e)}")

            # Show error details in expander
            with st.expander("Error Details"):
                st.code(str(e))


# For testing
if __name__ == "__main__":
    show()
