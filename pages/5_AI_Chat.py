"""
AI Chat Interface - Ask questions about UN sessions using RAG.

Features:
- Natural language questions about UN sessions
- Multi-query retrieval for better results
- Source citations with timestamps
- Filter by session, speaker, or country
- Conversation history
"""

import streamlit as st
import asyncio
from backend.services.rag_service import rag_service
from backend.services.vector_store import vector_store
from backend.services.embedding_service import embedding_service
from backend.services.database import db_service
from loguru import logger


# Page config
st.set_page_config(
    page_title="AI Chat - UN WebTV Analysis",
    page_icon="💬",
    layout="wide"
)

# Title
st.title("💬 AI Chat - Ask Questions About UN Sessions")
st.markdown("Use natural language to ask questions about UN WebTV sessions. The AI will search transcripts and provide answers with citations.")

# Initialize session state
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "vector_store_loaded" not in st.session_state:
    st.session_state.vector_store_loaded = False


# Sidebar - Filters and Settings
with st.sidebar:
    st.header("⚙️ Settings")

    # Search settings
    st.subheader("Search Settings")
    use_multi_query = st.checkbox(
        "Use Multi-Query Retrieval",
        value=True,
        help="Generate multiple search queries for better results"
    )

    top_k = st.slider(
        "Results to retrieve",
        min_value=3,
        max_value=20,
        value=10,
        help="Number of relevant segments to retrieve"
    )

    # Filters
    st.subheader("Filters")

    filter_session = st.text_input(
        "Session ID (optional)",
        placeholder="e.g., k1251fzd6n",
        help="Limit search to specific session"
    )

    filter_speaker = st.text_input(
        "Speaker Name (optional)",
        placeholder="e.g., Ambassador Smith",
        help="Limit search to specific speaker"
    )

    filter_country = st.text_input(
        "Country (optional)",
        placeholder="e.g., United States",
        help="Limit search to specific country"
    )

    st.divider()

    # Stats
    st.subheader("📊 Stats")
    vector_stats = vector_store.get_stats()
    st.metric("Total Segments", vector_stats["total_segments"])
    st.metric("Unique Sessions", vector_stats["unique_sessions"])

    cache_stats = embedding_service.get_cache_stats()
    st.metric("Cache Hit Rate", f"{cache_stats['hit_rate_percent']:.1f}%")

    st.divider()

    # Clear chat
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.chat_messages = []
        st.session_state.chat_history = []
        st.rerun()


# Main content
if vector_store.get_stats()["total_segments"] == 0:
    st.warning("""
    ⚠️ **No transcript data loaded in vector store.**

    The RAG chat system requires processed session transcripts to be loaded into the vector store.

    **To use this feature:**
    1. Process sessions from the "New Analysis" or "Batch Processing" pages
    2. Transcripts will be automatically embedded and loaded into the vector store
    3. Come back here to ask questions!

    **For testing:** You can run the test script to load sample data:
    ```bash
    python test_rag_system.py
    ```
    """)

    st.info("""
    **💡 Example Questions You Could Ask:**
    - "What did China say about extraterritorial jurisdiction?"
    - "Which countries support mandatory due diligence for corporations?"
    - "What concerns did developing countries raise?"
    - "How did Russia's position differ from the EU's position?"
    - "What SDGs were mentioned most frequently?"
    """)

    st.stop()


# Display chat history
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display sources if available
        if message["role"] == "assistant" and "sources" in message:
            with st.expander(f"📚 View {len(message['sources'])} Sources"):
                for source in message["sources"]:
                    st.markdown(f"""
                    **[{source['rank']}] {source['speaker_name']} ({source['country']})** - Similarity: {source['similarity_score']}

                    *{source['session_title']}*
                    Time: {source['start_time']} - {source['end_time']}

                    > {source['text'][:300]}...
                    """)
                    st.divider()

        # Display metadata if available
        if message["role"] == "assistant" and "metadata" in message:
            meta = message["metadata"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"📊 Retrieved: {meta['segments_retrieved']}")
            with col2:
                st.caption(f"📝 Cited: {meta['sources_cited']}")
            with col3:
                st.caption(f"🔤 Tokens: {meta['tokens_used']}")


# Chat input
if prompt := st.chat_input("Ask a question about the UN sessions..."):
    # Add user message to chat
    st.session_state.chat_messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching transcripts..."):
            try:
                # Build filters
                filters = {}
                if filter_session:
                    filters["session_id"] = filter_session.strip()
                if filter_speaker:
                    filters["speaker_name"] = filter_speaker.strip()
                if filter_country:
                    filters["country"] = filter_country.strip()

                # Get answer from RAG
                result = asyncio.run(
                    rag_service.answer_question(
                        question=prompt,
                        chat_history=st.session_state.chat_history,
                        top_k=top_k,
                        use_multi_query=use_multi_query,
                        **filters
                    )
                )

                # Display answer
                st.markdown(result["answer"])

                # Display sources
                if result["sources"]:
                    with st.expander(f"📚 View {len(result['sources'])} Sources"):
                        for source in result["sources"]:
                            st.markdown(f"""
                            **[{source['rank']}] {source['speaker_name']} ({source['country']})** - Similarity: {source['similarity_score']}

                            *{source['session_title']}*
                            Time: {source['start_time']} - {source['end_time']}

                            > {source['text'][:300]}...
                            """)
                            st.divider()

                # Display metadata
                meta = result["metadata"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"📊 Retrieved: {meta['segments_retrieved']}")
                with col2:
                    st.caption(f"📝 Cited: {meta['sources_cited']}")
                with col3:
                    st.caption(f"🔤 Tokens: {meta['tokens_used']}")

                # Add assistant message to chat
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["sources"],
                    "metadata": meta
                })

                # Update chat history (for context in next questions)
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                st.session_state.chat_history.append({"role": "assistant", "content": result["answer"]})

                # Keep only last 10 messages (5 exchanges) for context
                if len(st.session_state.chat_history) > 10:
                    st.session_state.chat_history = st.session_state.chat_history[-10:]

                st.rerun()

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                logger.error(f"Error in chat: {str(e)}")


# Example questions
if not st.session_state.chat_messages:
    st.markdown("---")
    st.subheader("💡 Example Questions to Get Started")

    example_questions = [
        "What did China say about extraterritorial jurisdiction?",
        "Which countries support mandatory due diligence for corporations?",
        "What concerns did developing countries raise about corporate accountability?",
        "How did Russia's position differ from the European Union's position?",
        "What SDGs were mentioned in the discussion?",
        "Who spoke about human rights violations in supply chains?",
        "What did civil society representatives emphasize?",
        "Did any countries co-sponsor the EU proposal?"
    ]

    cols = st.columns(2)
    for idx, question in enumerate(example_questions):
        with cols[idx % 2]:
            if st.button(question, key=f"example_{idx}", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": question})
                st.rerun()


# Footer
st.markdown("---")
st.caption("""
**Powered by Advanced RAG (Retrieval-Augmented Generation)**
- Multi-query retrieval for better recall
- Automatic source citations with timestamps
- Conversation context across questions
- Fast embedding caching for repeated queries
""")
