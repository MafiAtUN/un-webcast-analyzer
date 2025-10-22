"""Quick script to delete incomplete session from database."""
import asyncio
from backend.services.database import db_service

async def main():
    await db_service.initialize()

    # Delete the incomplete session
    session_id = "k1y7kgo2oc"

    try:
        db_service.sessions_container.delete_item(
            item=session_id,
            partition_key=session_id
        )
        print(f"✅ Deleted session: {session_id}")
    except Exception as e:
        print(f"❌ Error deleting session: {e}")

if __name__ == "__main__":
    asyncio.run(main())
