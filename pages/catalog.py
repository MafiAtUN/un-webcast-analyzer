"""
Catalog Page
Browse and search previously processed sessions.
"""

import streamlit as st
import asyncio
from datetime import datetime
from loguru import logger


def show():
    """Display the catalog page."""
    st.title("📚 Session Catalog")

    st.markdown("""
    Browse all previously processed UN WebTV sessions. Click on a session to view details or start chatting.
    """)

    st.markdown("---")

    # Initialize database
    from backend.services.database import db_service

    try:
        asyncio.run(db_service.initialize())
    except Exception as e:
        st.error(f"❌ Failed to connect to database: {str(e)}")
        return

    # Filters
    with st.expander("🔍 Filters"):
        col1, col2, col3 = st.columns(3)

        with col1:
            date_filter = st.date_input("Date Range", value=None)

        with col2:
            category_filter = st.multiselect(
                "Categories",
                ["Human Rights", "Development", "Peace & Security", "Climate"],
                default=None
            )

        with col3:
            search_query = st.text_input("Search", placeholder="Search sessions...")

    # Fetch sessions
    with st.spinner("Loading sessions..."):
        try:
            sessions = asyncio.run(db_service.list_sessions(limit=50))

            if not sessions:
                st.info("📭 No sessions found. Process your first session using the '➕ New Analysis' page!")
                return

            st.success(f"Found {len(sessions)} sessions")

            # Display sessions in cards
            for session in sessions:
                with st.container():
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.subheader(session.title)

                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            if session.date:
                                st.caption(f"📅 {session.date.strftime('%Y-%m-%d')}")

                        with col_b:
                            st.caption(f"⏱️ {session.duration_seconds // 60} min")

                        with col_c:
                            status_emoji = {
                                "completed": "✅",
                                "processing": "⏳",
                                "failed": "❌",
                                "pending": "⏳"
                            }
                            st.caption(f"{status_emoji.get(session.processing_status, '⏳')} {session.processing_status.title()}")

                        # Summary
                        if session.summary:
                            with st.expander("📝 Summary"):
                                st.write(session.summary)

                        # Entity tags
                        if session.entities:
                            tags = []

                            if session.entities.countries:
                                tags.extend([f"🌍 {c}" for c in session.entities.countries[:3]])

                            if session.entities.sdgs:
                                tags.extend([f"🎯 SDG {s.number}" for s in session.entities.sdgs[:3]])

                            if tags:
                                st.caption(" • ".join(tags))

                    with col2:
                        if session.processing_status == "completed":
                            if st.button(f"💬 Chat", key=f"chat_{session.id}", use_container_width=True):
                                st.session_state.current_session_id = session.id
                                # Navigate to chat (implement later)
                                st.info("Chat feature coming soon!")

                            if st.button(f"📊 Details", key=f"details_{session.id}", use_container_width=True):
                                show_session_details(session)

                    st.markdown("---")

        except Exception as e:
            st.error(f"❌ Error loading sessions: {str(e)}")
            logger.error(f"Catalog error: {str(e)}")


def show_session_details(session):
    """
    Show detailed information about a session in a modal.

    Args:
        session: Session metadata
    """
    with st.expander(f"📊 Session Details: {session.id}", expanded=True):
        tab1, tab2, tab3 = st.tabs(["Overview", "Entities", "Metadata"])

        with tab1:
            st.markdown("### Overview")

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Title:** {session.title}")
                st.write(f"**Date:** {session.date.strftime('%Y-%m-%d') if session.date else 'N/A'}")
                st.write(f"**Duration:** {session.duration_seconds // 60} minutes")
                st.write(f"**Location:** {session.location or 'N/A'}")

            with col2:
                st.write(f"**Session Type:** {session.session_type or 'N/A'}")
                st.write(f"**Broadcasting Entity:** {session.broadcasting_entity or 'N/A'}")
                st.write(f"**Languages:** {', '.join(session.languages)}")
                st.write(f"**Status:** {session.processing_status}")

            if session.summary:
                st.markdown("### Summary")
                st.write(session.summary)

        with tab2:
            if session.entities:
                st.markdown("### Extracted Entities")

                if session.entities.countries:
                    st.markdown("**Countries:**")
                    st.write(", ".join(session.entities.countries))

                if session.entities.speakers:
                    st.markdown("**Speakers:**")
                    for speaker in session.entities.speakers:
                        st.write(f"- {speaker.name} ({speaker.country or 'N/A'})")

                if session.entities.sdgs:
                    st.markdown("**SDGs:**")
                    for sdg in session.entities.sdgs:
                        st.write(f"- SDG {sdg.number}: {sdg.name}")

                if session.entities.topics:
                    st.markdown("**Topics:**")
                    st.write(", ".join(session.entities.topics))

                if session.entities.organizations:
                    st.markdown("**Organizations:**")
                    st.write(", ".join(session.entities.organizations))

        with tab3:
            st.markdown("### Technical Metadata")

            st.write(f"**Session ID:** {session.id}")
            st.write(f"**Kaltura Entry ID:** {session.kaltura_entry_id}")
            st.write(f"**URL:** [{session.url}]({session.url})")
            st.write(f"**Processed Date:** {session.processed_date.strftime('%Y-%m-%d %H:%M:%S') if session.processed_date else 'N/A'}")
            st.write(f"**View Count:** {session.view_count}")
            st.write(f"**Chat Count:** {session.chat_count}")


# For testing
if __name__ == "__main__":
    show()
