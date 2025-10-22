"""
Streamlit page for batch processing multiple UN WebTV videos in parallel.
"""
import streamlit as st
import asyncio
from backend.services.batch_processor import batch_processor


def main():
    st.title("🚀 Batch Processing")
    st.markdown("Process multiple UN WebTV videos in parallel - paste multiple links!")

    # Instructions
    with st.expander("ℹ️ How to use Batch Processing"):
        st.markdown("""
        **Batch Processing allows you to process multiple videos simultaneously:**

        1. **Paste URLs** - Enter multiple UN WebTV URLs (one per line)
        2. **Set Concurrency** - Choose how many videos to process at once (default: 3)
        3. **Start Processing** - Click 'Start Batch Processing' and wait
        4. **Monitor Progress** - Watch real-time progress as videos are processed
        5. **Review Results** - See which videos succeeded/failed
        6. **Analyze** - Go to Session Catalog to analyze all completed sessions

        **Benefits:**
        - Process 10+ videos while you work on something else
        - Automatic rate limiting to respect Azure API limits
        - Each video processes independently
        - Failed videos don't affect successful ones
        """)

    # Input section
    st.subheader("📋 Enter UN WebTV URLs")

    urls_text = st.text_area(
        "Paste UN WebTV URLs (one per line)",
        height=200,
        placeholder="https://webtv.un.org/en/asset/k1y/k1y7kgo2oc\nhttps://webtv.un.org/en/asset/k12/k1251fzd6n\n...",
        help="Enter multiple URLs, each on a new line"
    )

    # Parse URLs
    urls = [url.strip() for url in urls_text.split('\n') if url.strip()]

    # Show URL count
    if urls:
        st.info(f"📊 {len(urls)} URLs ready to process")

        # Show URLs in expander
        with st.expander(f"View all {len(urls)} URLs"):
            for i, url in enumerate(urls, 1):
                st.text(f"{i}. {url}")

    # Concurrency settings
    col1, col2 = st.columns(2)
    with col1:
        max_concurrent = st.number_input(
            "Max concurrent videos",
            min_value=1,
            max_value=10,
            value=3,
            help="How many videos to process simultaneously (recommended: 3-5)"
        )

    with col2:
        st.metric("Total Videos", len(urls))

    # Start processing button
    if st.button("🚀 Start Batch Processing", disabled=len(urls) == 0, type="primary"):
        if not urls:
            st.error("⚠️ Please enter at least one URL")
        else:
            # Create progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()

            # Progress callback
            async def update_progress(completed, total, current_url):
                progress = completed / total
                progress_bar.progress(progress)
                status_text.text(f"Processing: {completed}/{total} completed - Last: {current_url}")

            # Run batch processing
            status_text.text("🔌 Initializing...")

            # Update batch processor concurrency
            batch_processor.max_concurrent = max_concurrent
            batch_processor.semaphore = asyncio.Semaphore(max_concurrent)

            try:
                # Run async batch processing
                results = asyncio.run(
                    batch_processor.process_batch(
                        urls=urls,
                        progress_callback=update_progress
                    )
                )

                # Show final results
                progress_bar.progress(1.0)
                status_text.text("✅ Batch processing complete!")

                # Display results
                st.success(f"✅ Processed {results['completed']} / {results['total']} videos successfully")

                if results['failed'] > 0:
                    st.warning(f"⚠️ {results['failed']} videos failed")

                # Detailed results
                st.subheader("📊 Detailed Results")

                for url, result in results['sessions'].items():
                    status = result['status']

                    if status == "success":
                        with st.expander(f"✅ {url}", expanded=False):
                            data = result.get('data', {})

                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("Session ID", result.get('session_id', 'N/A'))

                            # Transcript stats
                            if data.get('transcript_summary'):
                                ts = data['transcript_summary']
                                with col2:
                                    st.metric("Segments", ts.get('total_segments', 0))
                                with col3:
                                    st.metric("Speakers", ts.get('unique_speakers', 0))

                            # Entity stats
                            if data.get('entities_summary'):
                                es = data['entities_summary']
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Speakers", es.get('speakers_count', 0))
                                with col2:
                                    st.metric("Countries", es.get('countries_count', 0))
                                with col3:
                                    st.metric("SDGs", es.get('sdgs_count', 0))
                                with col4:
                                    st.metric("Topics", es.get('topics_count', 0))

                    else:
                        with st.expander(f"❌ {url}", expanded=False):
                            st.error(f"Error: {result.get('error', 'Unknown error')}")

                # Next steps
                st.info("💡 Go to 'Session Catalog' to analyze all completed sessions!")

            except Exception as e:
                st.error(f"❌ Batch processing failed: {str(e)}")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())

    # Tips section
    st.markdown("---")
    st.subheader("💡 Tips for Batch Processing")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Optimal Settings:**
        - **3-5 concurrent** for best performance
        - **Azure rate limits** apply per subscription
        - **Large videos** take 30-60 minutes each
        - **Small videos** take 3-5 minutes each
        """)

    with col2:
        st.markdown("""
        **Best Practices:**
        - Mix small and large videos for faster completion
        - Process overnight for large batches
        - Check Azure OpenAI quotas before large batches
        - Monitor Cosmos DB usage for large batches
        """)


if __name__ == "__main__":
    main()
