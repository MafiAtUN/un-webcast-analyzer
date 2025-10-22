"""
Comprehensive verification of the complete workflow including chat functionality.
"""

import asyncio
from backend.services.database import db_service
from backend.services.azure_openai_client import azure_openai_client
from loguru import logger

async def verify_workflow():
    """Verify the complete workflow and data storage."""

    print("=" * 80)
    print("COMPREHENSIVE WORKFLOW VERIFICATION")
    print("=" * 80)

    # Initialize database
    await db_service.initialize()
    print("\n✅ Database initialized")

    # Get the session we just processed
    session_id = "k1251fzd6n"

    # 1. Verify Session Data
    print("\n1. VERIFYING SESSION DATA")
    print("-" * 80)
    session = db_service.sessions_container.read_item(
        item=session_id,
        partition_key=session_id
    )

    print(f"📝 Title: {session.get('title', 'N/A')}")
    print(f"📅 Date: {session.get('date', 'N/A')}")
    duration = session.get('duration_seconds', 0)
    print(f"⏱️  Duration: {duration}s ({duration//60} minutes)")
    print(f"📊 Status: {session.get('status', 'N/A')}")
    print(f"🔢 Progress: {session.get('progress', 0)}%")

    # 2. Verify Transcript Data
    print("\n2. VERIFYING TRANSCRIPT DATA")
    print("-" * 80)

    try:
        transcript = db_service.transcripts_container.read_item(
            item=session_id,
            partition_key=session_id
        )

        full_text = transcript.get('full_text', '')
        segments = transcript.get('segments', [])

        print(f"📄 Full transcript length: {len(full_text)} characters")
        print(f"📋 Number of segments: {len(segments)}")

        if segments:
            print(f"\n📍 First segment:")
            print(f"   Speaker: {segments[0].get('speaker_id', 'N/A')}")
            print(f"   Time: {segments[0].get('start_time', 'N/A')} - {segments[0].get('end_time', 'N/A')}")
            print(f"   Text: {segments[0].get('text', '')[:100]}...")

            print(f"\n📍 Last segment:")
            print(f"   Speaker: {segments[-1].get('speaker_id', 'N/A')}")
            print(f"   Time: {segments[-1].get('start_time', 'N/A')} - {segments[-1].get('end_time', 'N/A')}")
            print(f"   Text: {segments[-1].get('text', '')[:100]}...")

    except Exception as e:
        print(f"❌ Error reading transcript: {e}")

    # 3. Verify Entity Extraction
    print("\n3. VERIFYING ENTITY EXTRACTION")
    print("-" * 80)

    entities = session.get('entities', {})

    countries = entities.get('countries', [])
    speakers = entities.get('speakers', [])
    sdgs = entities.get('sdgs', [])
    topics = entities.get('topics', [])
    organizations = entities.get('organizations', [])

    print(f"🌍 Countries mentioned: {len(countries)}")
    if countries:
        print(f"   Examples: {', '.join(countries[:5])}")

    print(f"👤 Speakers identified: {len(speakers)}")
    if speakers:
        print(f"   Examples: {speakers[:3]}")

    print(f"🎯 SDGs mentioned: {len(sdgs)}")
    if sdgs:
        print(f"   Examples: {sdgs[:3]}")

    print(f"📋 Topics discussed: {len(topics)}")
    if topics:
        print(f"   Examples: {', '.join(topics[:5])}")

    print(f"🏛️  Organizations mentioned: {len(organizations)}")
    if organizations:
        print(f"   Examples: {', '.join(organizations[:5])}")

    # 4. Verify Summary
    print("\n4. VERIFYING SUMMARY GENERATION")
    print("-" * 80)

    summary = session.get('summary', '')
    print(f"📖 Summary length: {len(summary)} characters")
    print(f"\nSummary preview:")
    print(summary[:500] + "..." if len(summary) > 500 else summary)

    # 5. Test Chat Functionality with RAG
    print("\n5. TESTING CHAT FUNCTIONALITY")
    print("-" * 80)

    # Get transcript text for context
    try:
        transcript = db_service.transcripts_container.read_item(
            item=session_id,
            partition_key=session_id
        )
        transcript_text = transcript.get('full_text', '')

        # Test questions
        test_questions = [
            "What are the main topics discussed in this session?",
            "Which countries were mentioned?",
            "What were the key decisions or outcomes?"
        ]

        for i, question in enumerate(test_questions, 1):
            print(f"\n❓ Question {i}: {question}")

            try:
                # Create chat prompt with RAG context
                system_prompt = f"""You are an AI assistant helping analyze UN session transcripts.
You have access to the following session information:

Title: {session['title']}
Date: {session['date']}
Summary: {summary[:1000]}

Transcript excerpt: {transcript_text[:5000]}

Answer questions based on this information."""

                response = azure_openai_client.client.chat.completions.create(
                    model="gpt-4o-unga",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )

                answer = response.choices[0].message.content
                print(f"💬 Answer: {answer}")

            except Exception as e:
                print(f"❌ Error in chat: {e}")

    except Exception as e:
        print(f"❌ Error testing chat: {e}")

    # 6. Database Statistics
    print("\n6. DATABASE STATISTICS")
    print("-" * 80)

    # Count all sessions
    query = "SELECT VALUE COUNT(1) FROM c"
    session_count = list(db_service.sessions_container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))[0]

    print(f"📊 Total sessions in database: {session_count}")

    # Count transcripts
    transcript_count = list(db_service.transcripts_container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))[0]

    print(f"📄 Total transcripts in database: {transcript_count}")

    print("\n" + "=" * 80)
    print("✅ WORKFLOW VERIFICATION COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(verify_workflow())
