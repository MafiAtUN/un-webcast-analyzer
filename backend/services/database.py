"""
Database Service
Handles all database operations with Azure Cosmos DB.
"""

from typing import List, Optional, Dict, Any
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from loguru import logger
from config import settings
from backend.models.session import SessionMetadata, Transcript, Chat


class DatabaseService:
    """Service for Azure Cosmos DB operations."""

    def __init__(self):
        """Initialize database service."""
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.sessions_container = None
        self.transcripts_container = None
        self.speakers_container = None
        self.chats_container = None

    async def initialize(self) -> bool:
        """
        Initialize database connection and containers.

        Returns:
            True if successful
        """
        try:
            if not settings.COSMOS_ENDPOINT or not settings.COSMOS_KEY:
                logger.warning("Cosmos DB credentials not configured")
                return False

            logger.info("Initializing Cosmos DB connection...")

            # Create client
            self.client = CosmosClient(
                settings.COSMOS_ENDPOINT,
                settings.COSMOS_KEY
            )

            # Create database if not exists
            self.database = self.client.create_database_if_not_exists(
                id=settings.COSMOS_DATABASE_NAME
            )

            # Create containers if not exist
            self.sessions_container = self.database.create_container_if_not_exists(
                id=settings.COSMOS_SESSIONS_CONTAINER,
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400  # Minimum RU/s
            )

            self.transcripts_container = self.database.create_container_if_not_exists(
                id=settings.COSMOS_TRANSCRIPTS_CONTAINER,
                partition_key=PartitionKey(path="/session_id"),
                offer_throughput=400
            )

            self.speakers_container = self.database.create_container_if_not_exists(
                id=settings.COSMOS_SPEAKERS_CONTAINER,
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400
            )

            self.chats_container = self.database.create_container_if_not_exists(
                id=settings.COSMOS_CHATS_CONTAINER,
                partition_key=PartitionKey(path="/session_id"),
                offer_throughput=400
            )

            logger.info("Cosmos DB initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB: {str(e)}")
            return False

    # Session Operations

    async def create_session(self, session: SessionMetadata) -> bool:
        """
        Create a new session document.

        Args:
            session: Session metadata

        Returns:
            True if successful
        """
        try:
            session_dict = session.model_dump(mode='json')
            self.sessions_container.create_item(body=session_dict)
            logger.info(f"Created session: {session.id}")
            return True

        except CosmosHttpResponseError as e:
            logger.error(f"Failed to create session: {str(e)}")
            return False

    async def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session metadata or None
        """
        try:
            item = self.sessions_container.read_item(
                item=session_id,
                partition_key=session_id
            )
            return SessionMetadata(**item)

        except CosmosResourceNotFoundError:
            logger.warning(f"Session not found: {session_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}")
            return None

    async def update_session(self, session: SessionMetadata) -> bool:
        """
        Update existing session.

        Args:
            session: Updated session metadata

        Returns:
            True if successful
        """
        try:
            session_dict = session.model_dump(mode='json')
            self.sessions_container.upsert_item(body=session_dict)
            logger.info(f"Updated session: {session.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update session: {str(e)}")
            return False

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SessionMetadata]:
        """
        List sessions with optional filtering.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            filters: Optional filters

        Returns:
            List of sessions
        """
        try:
            # Build query
            query = "SELECT * FROM c ORDER BY c.date DESC"

            # Execute query
            items = list(self.sessions_container.query_items(
                query=query,
                enable_cross_partition_query=True,
                max_item_count=limit
            ))

            # Convert to models
            sessions = [SessionMetadata(**item) for item in items[offset:offset + limit]]
            logger.info(f"Retrieved {len(sessions)} sessions")
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            return []

    async def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if exists
        """
        session = await self.get_session(session_id)
        return session is not None

    # Transcript Operations

    async def create_transcript(self, transcript: Transcript) -> bool:
        """
        Create transcript document.

        Args:
            transcript: Transcript data

        Returns:
            True if successful
        """
        try:
            transcript_dict = transcript.model_dump(mode='json')
            self.transcripts_container.create_item(body=transcript_dict)
            logger.info(f"Created transcript for session: {transcript.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create transcript: {str(e)}")
            return False

    async def get_transcript(self, session_id: str) -> Optional[Transcript]:
        """
        Get transcript by session ID.

        Args:
            session_id: Session identifier

        Returns:
            Transcript or None
        """
        try:
            query = f"SELECT * FROM c WHERE c.session_id = '{session_id}'"
            items = list(self.transcripts_container.query_items(
                query=query,
                partition_key=session_id,
                max_item_count=1
            ))

            if items:
                return Transcript(**items[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get transcript: {str(e)}")
            return None

    # Chat Operations

    async def create_chat(self, chat: Chat) -> bool:
        """
        Create chat session.

        Args:
            chat: Chat data

        Returns:
            True if successful
        """
        try:
            chat_dict = chat.model_dump(mode='json')
            self.chats_container.create_item(body=chat_dict)
            logger.info(f"Created chat: {chat.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create chat: {str(e)}")
            return False

    async def update_chat(self, chat: Chat) -> bool:
        """
        Update chat session.

        Args:
            chat: Updated chat data

        Returns:
            True if successful
        """
        try:
            chat_dict = chat.model_dump(mode='json')
            self.chats_container.upsert_item(body=chat_dict)
            logger.info(f"Updated chat: {chat.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update chat: {str(e)}")
            return False

    async def get_chat(self, chat_id: str, session_id: str) -> Optional[Chat]:
        """
        Get chat by ID.

        Args:
            chat_id: Chat identifier
            session_id: Session identifier (partition key)

        Returns:
            Chat or None
        """
        try:
            item = self.chats_container.read_item(
                item=chat_id,
                partition_key=session_id
            )
            return Chat(**item)

        except CosmosResourceNotFoundError:
            return None

        except Exception as e:
            logger.error(f"Failed to get chat: {str(e)}")
            return None

    async def list_chats_for_session(self, session_id: str) -> List[Chat]:
        """
        List all chats for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of chats
        """
        try:
            query = f"SELECT * FROM c WHERE c.session_id = '{session_id}' ORDER BY c.created_date DESC"
            items = list(self.chats_container.query_items(
                query=query,
                partition_key=session_id
            ))

            chats = [Chat(**item) for item in items]
            logger.info(f"Retrieved {len(chats)} chats for session {session_id}")
            return chats

        except Exception as e:
            logger.error(f"Failed to list chats: {str(e)}")
            return []


# Singleton instance
db_service = DatabaseService()
