"""
Test the complete workflow with a small video to verify the fix.
"""

import asyncio
from backend.services.session_processor import session_processor
from backend.services.database import db_service
from loguru import logger

async def test_small_session():
    """Test with a small UN video."""

    # Small video URL (should be quick - under 3 minutes)
    url = "https://webtv.un.org/en/asset/k1y/k1y7kgo2oc"
    session_id = "k1y7kgo2oc"

    print("=" * 80)
    print("TESTING COMPLETE WORKFLOW WITH SMALL VIDEO")
    print("=" * 80)

    # Initialize database
    await db_service.initialize()
    print("\n✅ Database initialized")

    # Delete session if it exists
    try:
        db_service.sessions_container.delete_item(
            item=session_id,
            partition_key=session_id
        )
        print(f"✅ Deleted existing session: {session_id}")
    except:
        print(f"ℹ️  No existing session to delete")

    # Process the session
    print(f"\n🚀 Processing session: {url}")
    print("   This should take about 30-60 seconds...")

    try:
        await session_processor.process_session(url, session_id)
        print("\n" + "=" * 80)
        print("✅ SESSION PROCESSED SUCCESSFULLY!")
        print("=" * 80)

        # Verify the data
        print("\n📊 VERIFICATION:")
        print("-" * 80)

        # Get session data
        session = db_service.sessions_container.read_item(
            item=session_id,
            partition_key=session_id
        )

        print(f"\n1. SESSION DATA:")
        print(f"   Title: {session.get('title', 'N/A')}")
        print(f"   Date: {session.get('date', 'N/A')}")
        print(f"   Duration: {session.get('duration_seconds', 0)}s")
        print(f"   Status: {session.get('status', 'N/A')}")

        # Get transcript data
        try:
            transcript = db_service.transcripts_container.read_item(
                item=session_id,
                partition_key=session_id
            )

            segments = transcript.get('segments', [])
            full_text = transcript.get('full_text', '')

            print(f"\n2. TRANSCRIPT DATA:")
            print(f"   ✅ Full text length: {len(full_text)} characters")
            print(f"   ✅ Number of segments: {len(segments)}")

            if segments:
                print(f"\n   First segment:")
                print(f"     Speaker: {segments[0].get('speaker_id', 'N/A')}")
                print(f"     Time: {segments[0].get('start_time', 'N/A')} - {segments[0].get('end_time', 'N/A')}")
                print(f"     Text: {segments[0].get('text', '')[:80]}...")

                print(f"\n   Last segment:")
                print(f"     Speaker: {segments[-1].get('speaker_id', 'N/A')}")
                print(f"     Time: {segments[-1].get('start_time', 'N/A')} - {segments[-1].get('end_time', 'N/A')}")
                print(f"     Text: {segments[-1].get('text', '')[:80]}...")

                # Count unique speakers
                unique_speakers = set(s.get('speaker_id', '') for s in segments)
                print(f"\n   ✅ Unique speakers identified: {len(unique_speakers)}")
                print(f"      Speakers: {', '.join(sorted(unique_speakers))}")
            else:
                print(f"   ❌ NO SEGMENTS FOUND!")

        except Exception as e:
            print(f"\n   ❌ Error reading transcript: {e}")

        # Get entities
        entities = session.get('entities', {})

        print(f"\n3. ENTITY EXTRACTION:")
        countries = entities.get('countries', [])
        speakers_list = entities.get('speakers', [])
        sdgs = entities.get('sdgs', [])
        topics = entities.get('topics', [])
        organizations = entities.get('organizations', [])

        print(f"   Countries: {len(countries)}")
        if countries:
            print(f"     {', '.join(countries[:5])}")

        print(f"   Speakers: {len(speakers_list)}")
        if speakers_list:
            print(f"     {speakers_list[:3]}")

        print(f"   SDGs: {len(sdgs)}")
        if sdgs:
            print(f"     {sdgs[:3]}")

        print(f"   Topics: {len(topics)}")
        if topics:
            print(f"     {', '.join(topics[:5])}")

        print(f"   Organizations: {len(organizations)}")
        if organizations:
            print(f"     {', '.join(organizations[:5])}")

        # Get summary
        summary = session.get('summary', '')
        print(f"\n4. SUMMARY:")
        print(f"   Length: {len(summary)} characters")
        print(f"   Preview: {summary[:200]}...")

        print("\n" + "=" * 80)
        if len(segments) > 0 and len(countries) > 0:
            print("✅✅✅ ALL FEATURES WORKING! ✅✅✅")
        elif len(segments) > 0:
            print("⚠️  PARTIAL SUCCESS - Transcript works but entities may be incomplete")
        else:
            print("❌ FAILED - No transcript segments found")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_small_session())
