"""
UN WebTV Analysis Platform - Visualizations Page
Interactive visualizations for session analysis with download capabilities.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import json
import io
import base64
from wordcloud import WordCloud
import matplotlib.pyplot as plt

from backend.services.database import db_service


async def get_all_sessions():
    """Fetch all available sessions from database."""
    try:
        await db_service.initialize()
        sessions = []
        query = "SELECT * FROM c WHERE c.type = 'session' ORDER BY c.date DESC"
        items = db_service.sessions_container.query_items(
            query=query,
            enable_cross_partition_query=True
        )
        for item in items:
            sessions.append(item)
        return sessions
    except Exception as e:
        st.error(f"Error fetching sessions: {str(e)}")
        return []


async def get_session_details(session_id: str):
    """Fetch complete session details including transcript and entities."""
    try:
        await db_service.initialize()

        # Get session
        session = await db_service.get_session(session_id)

        # Get transcript
        transcript = None
        try:
            transcript = db_service.transcripts_container.read_item(
                item=session_id,
                partition_key=session_id
            )
        except:
            pass

        return session, transcript
    except Exception as e:
        st.error(f"Error fetching session details: {str(e)}")
        return None, None


def download_figure(fig, filename):
    """Generate download button for plotly figure."""
    buffer = io.BytesIO()
    fig.write_html(buffer)
    buffer.seek(0)

    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}.html">Download {filename}</a>'
    return href


def create_word_cloud(text: str, title: str = "Word Cloud"):
    """Create word cloud visualization."""
    if not text or len(text.strip()) < 10:
        return None

    # Create word cloud
    wordcloud = WordCloud(
        width=1200,
        height=600,
        background_color='white',
        colormap='viridis',
        max_words=100,
        relative_scaling=0.5,
        min_font_size=10
    ).generate(text)

    # Create matplotlib figure
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

    return fig


def create_speaker_distribution(session_data: dict):
    """Create speaker participation visualizations."""
    if not session_data or 'entities' not in session_data:
        return None

    entities = session_data.get('entities', {})
    speakers = entities.get('speakers', [])

    if not speakers:
        return None

    # Prepare data
    speaker_names = []
    countries = []

    for speaker in speakers:
        speaker_names.append(speaker.get('name', 'Unknown'))
        countries.append(speaker.get('country', 'Unknown'))

    df = pd.DataFrame({
        'Speaker': speaker_names,
        'Country': countries
    })

    # Count speakers
    speaker_counts = df['Speaker'].value_counts().head(15)

    # Create bar chart
    fig = go.Figure([
        go.Bar(
            x=speaker_counts.values,
            y=speaker_counts.index,
            orientation='h',
            marker=dict(
                color=speaker_counts.values,
                colorscale='Blues',
                showscale=True,
                colorbar=dict(title="Count")
            ),
            text=speaker_counts.values,
            textposition='auto',
        )
    ])

    fig.update_layout(
        title='Top 15 Speakers by Frequency',
        xaxis_title='Number of Mentions',
        yaxis_title='Speaker',
        height=500,
        showlegend=False,
        template='plotly_white'
    )

    return fig


def create_country_participation(session_data: dict):
    """Create country participation visualizations."""
    if not session_data or 'entities' not in session_data:
        return None

    entities = session_data.get('entities', {})
    countries = entities.get('countries', [])

    if not countries:
        return None

    # Count country mentions
    country_counts = Counter(countries)

    # Create DataFrame
    df = pd.DataFrame(
        country_counts.most_common(20),
        columns=['Country', 'Mentions']
    )

    # Create bar chart
    fig = px.bar(
        df,
        x='Mentions',
        y='Country',
        orientation='h',
        title='Top 20 Countries by Mentions',
        color='Mentions',
        color_continuous_scale='Teal',
        text='Mentions'
    )

    fig.update_layout(
        height=600,
        showlegend=False,
        template='plotly_white'
    )

    fig.update_traces(textposition='auto')

    return fig


def create_sdg_heatmap(session_data: dict):
    """Create SDG mentions heatmap."""
    if not session_data or 'entities' not in session_data:
        return None

    entities = session_data.get('entities', {})
    sdgs = entities.get('sdgs', [])

    if not sdgs:
        return None

    # SDG details
    sdg_names = {
        1: "No Poverty",
        2: "Zero Hunger",
        3: "Good Health",
        4: "Quality Education",
        5: "Gender Equality",
        6: "Clean Water",
        7: "Affordable Energy",
        8: "Decent Work",
        9: "Industry & Innovation",
        10: "Reduced Inequalities",
        11: "Sustainable Cities",
        12: "Responsible Consumption",
        13: "Climate Action",
        14: "Life Below Water",
        15: "Life on Land",
        16: "Peace & Justice",
        17: "Partnerships"
    }

    # Count SDG mentions
    sdg_counts = Counter()
    for sdg in sdgs:
        if isinstance(sdg, dict):
            sdg_num = sdg.get('number')
        else:
            sdg_num = sdg
        if sdg_num:
            sdg_counts[sdg_num] += 1

    # Create data for all SDGs
    sdg_data = []
    for i in range(1, 18):
        sdg_data.append({
            'SDG': f"SDG {i}",
            'Name': sdg_names.get(i, f"SDG {i}"),
            'Mentions': sdg_counts.get(i, 0)
        })

    df = pd.DataFrame(sdg_data)

    # Create bar chart
    fig = px.bar(
        df,
        x='SDG',
        y='Mentions',
        title='Sustainable Development Goals Mentioned',
        color='Mentions',
        color_continuous_scale='RdYlGn',
        hover_data=['Name'],
        text='Mentions'
    )

    fig.update_layout(
        height=500,
        template='plotly_white',
        xaxis_tickangle=-45
    )

    fig.update_traces(textposition='outside')

    return fig


def create_topic_distribution(session_data: dict):
    """Create topic distribution pie chart."""
    if not session_data or 'entities' not in session_data:
        return None

    entities = session_data.get('entities', {})
    topics = entities.get('topics', [])

    if not topics:
        return None

    # Count topics
    topic_counts = Counter(topics[:10])  # Top 10 topics

    # Create pie chart
    fig = go.Figure(data=[
        go.Pie(
            labels=list(topic_counts.keys()),
            values=list(topic_counts.values()),
            hole=0.3,
            marker=dict(
                colors=px.colors.qualitative.Set3,
                line=dict(color='white', width=2)
            ),
            textposition='inside',
            textinfo='label+percent'
        )
    ])

    fig.update_layout(
        title='Topic Distribution (Top 10)',
        height=500,
        template='plotly_white',
        showlegend=True
    )

    return fig


def create_organizations_network(session_data: dict):
    """Create organizations mention bar chart."""
    if not session_data or 'entities' not in session_data:
        return None

    entities = session_data.get('entities', {})
    organizations = entities.get('organizations', [])

    if not organizations:
        return None

    # Count organizations
    org_counts = Counter(organizations)

    # Create DataFrame
    df = pd.DataFrame(
        org_counts.most_common(15),
        columns=['Organization', 'Mentions']
    )

    # Create bar chart
    fig = px.bar(
        df,
        x='Mentions',
        y='Organization',
        orientation='h',
        title='Top 15 Organizations Mentioned',
        color='Mentions',
        color_continuous_scale='Purples',
        text='Mentions'
    )

    fig.update_layout(
        height=600,
        template='plotly_white'
    )

    fig.update_traces(textposition='auto')

    return fig


def create_speaker_timeline(transcript_data: dict):
    """Create speaker timeline (Gantt chart style)."""
    if not transcript_data or 'segments' not in transcript_data:
        return None

    segments = transcript_data.get('segments', [])

    if not segments:
        return None

    # Extract speaker segments (limit to first 50 for readability)
    speaker_segments = []
    for seg in segments[:50]:
        speaker = seg.get('speaker', 'Unknown')
        start = seg.get('start', 0)
        end = seg.get('end', 0)

        speaker_segments.append({
            'Speaker': speaker,
            'Start': start / 60,  # Convert to minutes
            'End': end / 60,
            'Duration': (end - start) / 60
        })

    df = pd.DataFrame(speaker_segments)

    # Create timeline
    fig = px.timeline(
        df,
        x_start='Start',
        x_end='End',
        y='Speaker',
        title='Speaker Timeline (First 50 Segments)',
        color='Speaker',
        hover_data=['Duration']
    )

    fig.update_layout(
        xaxis_title='Time (minutes)',
        yaxis_title='Speaker',
        height=600,
        template='plotly_white',
        showlegend=False
    )

    return fig


def create_speaking_time_analysis(transcript_data: dict):
    """Create speaking time analysis."""
    if not transcript_data or 'segments' not in transcript_data:
        return None

    segments = transcript_data.get('segments', [])

    if not segments:
        return None

    # Calculate speaking time per speaker
    speaker_times = {}
    for seg in segments:
        speaker = seg.get('speaker', 'Unknown')
        duration = seg.get('end', 0) - seg.get('start', 0)

        if speaker in speaker_times:
            speaker_times[speaker] += duration
        else:
            speaker_times[speaker] = duration

    # Convert to minutes and sort
    speaker_times_min = {k: v/60 for k, v in speaker_times.items()}
    sorted_speakers = sorted(speaker_times_min.items(), key=lambda x: x[1], reverse=True)[:15]

    # Create DataFrame
    df = pd.DataFrame(sorted_speakers, columns=['Speaker', 'Minutes'])

    # Create bar chart
    fig = px.bar(
        df,
        x='Minutes',
        y='Speaker',
        orientation='h',
        title='Speaking Time by Speaker (Top 15)',
        color='Minutes',
        color_continuous_scale='Oranges',
        text='Minutes'
    )

    fig.update_layout(
        height=600,
        template='plotly_white'
    )

    fig.update_traces(textposition='auto', texttemplate='%{text:.1f} min')

    return fig


def create_session_summary_metrics(session_data: dict, transcript_data: dict):
    """Create summary metrics visualization."""
    metrics = []

    # Session duration
    if session_data and 'duration_seconds' in session_data:
        duration_min = session_data['duration_seconds'] / 60
        metrics.append({
            'Metric': 'Duration',
            'Value': f"{duration_min:.1f} min"
        })

    # Speaker count
    if session_data and 'entities' in session_data:
        entities = session_data['entities']
        speakers = entities.get('speakers', [])
        metrics.append({
            'Metric': 'Speakers',
            'Value': len(speakers)
        })

        countries = entities.get('countries', [])
        metrics.append({
            'Metric': 'Countries',
            'Value': len(set(countries))
        })

        sdgs = entities.get('sdgs', [])
        metrics.append({
            'Metric': 'SDGs Mentioned',
            'Value': len(set([s if isinstance(s, int) else s.get('number') for s in sdgs]))
        })

        topics = entities.get('topics', [])
        metrics.append({
            'Metric': 'Topics',
            'Value': len(topics)
        })

    # Segment count
    if transcript_data and 'segments' in transcript_data:
        segments = transcript_data['segments']
        metrics.append({
            'Metric': 'Segments',
            'Value': len(segments)
        })

    if not metrics:
        return None

    df = pd.DataFrame(metrics)

    # Create metric cards using plotly
    fig = go.Figure()

    for i, row in df.iterrows():
        fig.add_trace(go.Indicator(
            mode="number",
            value=int(row['Value'].split()[0]) if row['Value'].split()[0].isdigit() else 0,
            title={'text': row['Metric']},
            domain={'row': 0, 'column': i}
        ))

    fig.update_layout(
        grid={'rows': 1, 'columns': len(metrics), 'pattern': "independent"},
        template='plotly_white',
        height=200,
        title='Session Metrics Overview'
    )

    return fig


def show():
    """Display visualizations page."""
    st.markdown('<div class="main-header">📊 Session Visualizations</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Interactive visual analytics for UN session data</div>', unsafe_allow_html=True)

    # Fetch sessions
    import asyncio
    sessions = asyncio.run(get_all_sessions())

    if not sessions:
        st.warning("No sessions available for visualization. Please process a session first.")
        return

    # Session selector
    st.markdown("### Select a Session")

    session_options = {
        f"{s.get('title', 'Untitled')} ({s.get('date', 'Unknown date')})": s.get('id')
        for s in sessions
    }

    selected_session_label = st.selectbox(
        "Choose a session to visualize:",
        options=list(session_options.keys())
    )

    selected_session_id = session_options[selected_session_label]

    # Fetch session details
    with st.spinner("Loading session data..."):
        session_data, transcript_data = asyncio.run(get_session_details(selected_session_id))

    if not session_data:
        st.error("Failed to load session data.")
        return

    # Display session info
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Title", session_data.get('title', 'N/A')[:30] + "...")

    with col2:
        st.metric("Date", session_data.get('date', 'N/A'))

    with col3:
        duration = session_data.get('duration_seconds', 0) / 60
        st.metric("Duration", f"{duration:.1f} min")

    st.markdown("---")

    # Tabs for different visualization categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Text Analysis",
        "👥 Speakers & Participation",
        "🎯 SDGs & Topics",
        "🌍 Geographic & Organizations",
        "⏱️ Timeline & Temporal"
    ])

    # TAB 1: Text Analysis
    with tab1:
        st.subheader("Text Analysis Visualizations")

        # Word Cloud
        if transcript_data and 'text' in transcript_data:
            st.markdown("#### Word Cloud")
            st.caption("Most frequent words in the session transcript")

            wc_fig = create_word_cloud(transcript_data['text'], "Session Word Cloud")
            if wc_fig:
                st.pyplot(wc_fig)

                # Download button
                buf = io.BytesIO()
                wc_fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                buf.seek(0)
                st.download_button(
                    label="Download Word Cloud",
                    data=buf,
                    file_name=f"wordcloud_{selected_session_id}.png",
                    mime="image/png"
                )
        else:
            st.info("Transcript not available for word cloud generation.")

    # TAB 2: Speakers & Participation
    with tab2:
        st.subheader("Speaker & Participation Analytics")

        # Speaker distribution
        st.markdown("#### Speaker Frequency")
        speaker_fig = create_speaker_distribution(session_data)
        if speaker_fig:
            st.plotly_chart(speaker_fig, use_container_width=True)
            st.download_button(
                label="Download Speaker Distribution",
                data=speaker_fig.to_html(),
                file_name=f"speaker_distribution_{selected_session_id}.html",
                mime="text/html"
            )
        else:
            st.info("Speaker data not available.")

        # Speaking time analysis
        st.markdown("#### Speaking Time Analysis")
        time_fig = create_speaking_time_analysis(transcript_data)
        if time_fig:
            st.plotly_chart(time_fig, use_container_width=True)
            st.download_button(
                label="Download Speaking Time Analysis",
                data=time_fig.to_html(),
                file_name=f"speaking_time_{selected_session_id}.html",
                mime="text/html"
            )
        else:
            st.info("Speaking time data not available.")

        # Speaker timeline
        st.markdown("#### Speaker Timeline")
        timeline_fig = create_speaker_timeline(transcript_data)
        if timeline_fig:
            st.plotly_chart(timeline_fig, use_container_width=True)
            st.download_button(
                label="Download Speaker Timeline",
                data=timeline_fig.to_html(),
                file_name=f"speaker_timeline_{selected_session_id}.html",
                mime="text/html"
            )
        else:
            st.info("Timeline data not available.")

    # TAB 3: SDGs & Topics
    with tab3:
        st.subheader("SDG & Topic Analysis")

        # SDG heatmap
        st.markdown("#### Sustainable Development Goals")
        sdg_fig = create_sdg_heatmap(session_data)
        if sdg_fig:
            st.plotly_chart(sdg_fig, use_container_width=True)
            st.download_button(
                label="Download SDG Analysis",
                data=sdg_fig.to_html(),
                file_name=f"sdg_analysis_{selected_session_id}.html",
                mime="text/html"
            )
        else:
            st.info("SDG data not available.")

        # Topic distribution
        st.markdown("#### Topic Distribution")
        topic_fig = create_topic_distribution(session_data)
        if topic_fig:
            st.plotly_chart(topic_fig, use_container_width=True)
            st.download_button(
                label="Download Topic Distribution",
                data=topic_fig.to_html(),
                file_name=f"topic_distribution_{selected_session_id}.html",
                mime="text/html"
            )
        else:
            st.info("Topic data not available.")

    # TAB 4: Geographic & Organizations
    with tab4:
        st.subheader("Geographic & Organizational Analysis")

        # Country participation
        st.markdown("#### Country Participation")
        country_fig = create_country_participation(session_data)
        if country_fig:
            st.plotly_chart(country_fig, use_container_width=True)
            st.download_button(
                label="Download Country Participation",
                data=country_fig.to_html(),
                file_name=f"country_participation_{selected_session_id}.html",
                mime="text/html"
            )
        else:
            st.info("Country data not available.")

        # Organizations
        st.markdown("#### Organizations Mentioned")
        org_fig = create_organizations_network(session_data)
        if org_fig:
            st.plotly_chart(org_fig, use_container_width=True)
            st.download_button(
                label="Download Organizations Analysis",
                data=org_fig.to_html(),
                file_name=f"organizations_{selected_session_id}.html",
                mime="text/html"
            )
        else:
            st.info("Organization data not available.")

    # TAB 5: Timeline & Temporal
    with tab5:
        st.subheader("Temporal Analysis")

        st.info("More temporal visualizations coming soon!")
        st.markdown("""
        Future additions:
        - Session pacing analysis
        - Topic evolution over time
        - Speaker intervention patterns
        - Comparative timeline across sessions
        """)

    # Summary section
    st.markdown("---")
    st.markdown("### 📋 Export All Visualizations")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Generate Full Report", type="primary"):
            st.success("Full report generation coming soon!")

    with col2:
        # Export session data as JSON
        export_data = {
            'session': session_data,
            'transcript': transcript_data
        }

        st.download_button(
            label="📥 Download Session Data (JSON)",
            data=json.dumps(export_data, indent=2),
            file_name=f"session_data_{selected_session_id}.json",
            mime="application/json"
        )
