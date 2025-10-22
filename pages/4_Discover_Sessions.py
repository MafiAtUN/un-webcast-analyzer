"""
Session Discovery Page
Browse, discover, and capture UN WebTV sessions directly from the portal.
"""
import streamlit as st
import asyncio
from datetime import datetime, timedelta
from backend.services.session_discovery import session_discovery
from backend.services.session_processor import session_processor
from backend.services.database import db_service
import pandas as pd


def main():
    st.set_page_config(page_title="Discover Sessions", page_icon="🔍", layout="wide")

    st.title("🔍 Discover UN WebTV Sessions")
    st.markdown("Browse and capture UN WebTV sessions directly - no need to visit the website!")

    # Tabs for different discovery methods
    tab1, tab2, tab3 = st.tabs([
        "📅 Browse by Date",
        "🏛️ Browse by UN Body",
        "⭐ Featured Sessions"
    ])

    # Tab 1: Browse by Date
    with tab1:
        st.subheader("📅 Browse Sessions by Date Range")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=7),
                max_value=datetime.now()
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now(),
                max_value=datetime.now()
            )

        if st.button("🔍 Search Sessions", key="search_by_date"):
            with st.spinner("Discovering sessions..."):
                # Convert dates to datetime
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date, datetime.max.time())

                # Discover sessions
                sessions = asyncio.run(
                    session_discovery.discover_sessions_by_date(start_dt, end_dt, limit=50)
                )

                if sessions:
                    st.success(f"✅ Found {len(sessions)} sessions")
                    display_sessions_grid(sessions)
                else:
                    st.warning("⚠️ No sessions found. Showing sample sessions instead.")
                    display_sessions_grid(session_discovery.get_sample_sessions())

    # Tab 2: Browse by UN Body
    with tab2:
        st.subheader("🏛️ Browse by UN Body")

        # UN Bodies
        bodies = {
            "🛡️ Security Council": "security-council",
            "🌐 General Assembly": "general-assembly",
            "👥 Human Rights Council": "human-rights-council",
            "💼 ECOSOC": "ecosoc",
            "📊 UNCTAD": "unctad",
            "🏥 WHO": "who",
            "🌍 UNEP": "unep",
        }

        selected_body = st.selectbox(
            "Select UN Body",
            options=list(bodies.keys()),
            help="Choose which UN body's sessions to browse"
        )

        if st.button("🔍 Browse Sessions", key="search_by_body"):
            with st.spinner(f"Loading {selected_body} sessions..."):
                body_slug = bodies[selected_body]
                sessions = asyncio.run(
                    session_discovery.get_sessions_by_body(body_slug, limit=20)
                )

                if sessions:
                    st.success(f"✅ Found {len(sessions)} sessions")
                    display_sessions_grid(sessions)
                else:
                    st.info(f"💡 No sessions found for {selected_body}. Showing sample sessions.")
                    display_sessions_grid(session_discovery.get_sample_sessions())

    # Tab 3: Featured/Sample Sessions
    with tab3:
        st.subheader("⭐ Featured Sessions")
        st.markdown("Hand-picked important sessions ready to analyze")

        # Get sample sessions
        featured_sessions = session_discovery.get_sample_sessions()
        display_sessions_grid(featured_sessions)


def display_sessions_grid(sessions):
    """Display sessions in a beautiful grid with capture buttons."""
    if not sessions:
        st.info("No sessions to display")
        return

    # Show sessions in cards (2 per row)
    cols_per_row = 2

    for i in range(0, len(sessions), cols_per_row):
        cols = st.columns(cols_per_row)

        for j in range(cols_per_row):
            idx = i + j
            if idx >= len(sessions):
                break

            session = sessions[idx]

            with cols[j]:
                display_session_card(session, idx)


def display_session_card(session, idx):
    """Display a single session as a card with capture button."""

    # Card container with styling
    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 250px;
        ">
            <h3 style="margin-top: 0; color: white;">{session.get('title', 'Unknown Session')[:60]}...</h3>
        </div>
        """, unsafe_allow_html=True)

        # Session details
        col1, col2 = st.columns(2)

        with col1:
            if session.get('body'):
                st.markdown(f"**🏛️ Body:** {session['body']}")
            if session.get('date'):
                date_str = session['date'].strftime('%b %d, %Y')
                st.markdown(f"**📅 Date:** {date_str}")

        with col2:
            if session.get('duration_est'):
                st.markdown(f"**⏱️ Duration:** {session['duration_est']}")
            if session.get('session_id'):
                st.markdown(f"**🆔 ID:** `{session['session_id']}`")

        # Check if already captured
        session_id = session.get('session_id')
        already_captured = False

        if session_id:
            try:
                existing = asyncio.run(check_if_captured(session_id))
                already_captured = existing is not None
            except:
                pass

        # Action buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if already_captured:
                st.success("✅ Captured")
            else:
                if st.button("📥 Capture", key=f"capture_{idx}", type="primary"):
                    capture_session(session)

        with col2:
            if already_captured:
                if st.button("👁️ View", key=f"view_{idx}"):
                    st.info(f"💡 Go to 'Session Catalog' to view session: {session_id}")

        with col3:
            url = session.get('url', '')
            if url:
                st.markdown(f"[🔗 Open]({url})", unsafe_allow_html=True)

        st.markdown("---")


async def check_if_captured(session_id: str):
    """Check if session is already in database."""
    try:
        await db_service.initialize()
        return await db_service.get_session(session_id)
    except:
        return None


def capture_session(session):
    """Capture a session - add to processing queue."""
    session_id = session.get('session_id')
    url = session.get('url')

    if not url:
        st.error("❌ No URL available for this session")
        return

    st.info(f"📥 Capturing session: {session.get('title')}")

    # Show options for capture
    with st.expander("⚙️ Capture Options", expanded=True):
        st.markdown("**Choose how to capture this session:**")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚀 Process Now", key=f"process_now_{session_id}", type="primary"):
                # Process immediately
                with st.spinner("Processing session... This may take a while."):
                    try:
                        result = asyncio.run(session_processor.process_session(url))

                        if result and result.get('status') == 'completed':
                            st.success(f"✅ Session captured and processed!")
                            st.balloons()

                            # Show summary
                            st.markdown("### 📊 Processing Summary")
                            if result.get('transcript_summary'):
                                ts = result['transcript_summary']
                                st.metric("Transcript Segments", ts.get('total_segments', 0))

                            if result.get('entities_summary'):
                                es = result['entities_summary']
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Speakers", es.get('speakers_count', 0))
                                with col2:
                                    st.metric("Countries", es.get('countries_count', 0))
                                with col3:
                                    st.metric("SDGs", es.get('sdgs_count', 0))

                            st.info("💡 Go to 'Session Catalog' to analyze this session")
                        else:
                            st.error("❌ Processing failed or incomplete")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        with col2:
            if st.button("📋 Add to Batch Queue", key=f"add_batch_{session_id}"):
                # Add to session state for batch processing
                if 'batch_queue' not in st.session_state:
                    st.session_state.batch_queue = []

                if url not in st.session_state.batch_queue:
                    st.session_state.batch_queue.append(url)
                    st.success(f"✅ Added to batch queue ({len(st.session_state.batch_queue)} sessions)")
                    st.info("💡 Go to 'Batch Processing' to process all queued sessions")
                else:
                    st.warning("⚠️ Already in batch queue")

    # Show batch queue status
    if 'batch_queue' in st.session_state and st.session_state.batch_queue:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📋 Batch Queue")
        st.sidebar.info(f"{len(st.session_state.batch_queue)} sessions queued")
        if st.sidebar.button("🚀 Process Queue"):
            st.sidebar.info("💡 Go to 'Batch Processing' page to process all sessions")


if __name__ == "__main__":
    main()
