"""Test the complete workflow with a UN WebTV session."""
import asyncio
from backend.services.session_processor import session_processor
from backend.services.database import db_service

async def main():
    url = "https://webtv.un.org/en/asset/k12/k1251fzd6n"

    print(f"🚀 Testing workflow with URL: {url}")
    print("=" * 80)

    # Initialize database
    print("🔌 Initializing database...")
    await db_service.initialize()
    print("✅ Database initialized")

    try:
        session = await session_processor.process_session(url)

        if session:
            print("\n✅ SESSION PROCESSED SUCCESSFULLY!")
            print("=" * 80)
            print(f"📝 Title: {session.title}")
            print(f"📅 Date: {session.date}")
            print(f"⏱️  Duration: {session.duration_seconds}s ({session.duration_seconds // 60}min)")
            print(f"🔊 Audio URL: {session.audio_blob_url}")
            print(f"📄 Transcript URL: {session.transcript_blob_url}")
            print(f"📊 Status: {session.processing_status}")

            if session.entities:
                print(f"\n🌍 Countries: {', '.join(session.entities.countries[:5])}...")
                print(f"👤 Speakers: {len(session.entities.speakers)}")
                print(f"🎯 SDGs: {len(session.entities.sdgs)}")
                print(f"📋 Topics: {', '.join(session.entities.topics[:3])}...")

            if session.summary:
                print(f"\n📖 Summary:\n{session.summary[:200]}...")

        else:
            print("\n❌ FAILED: No session returned")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
