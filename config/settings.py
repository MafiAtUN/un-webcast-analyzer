"""
Application configuration and settings.
Uses Pydantic for validation and environment variable management.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "UN WebTV Analysis Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o-unga"

    # Model Deployments
    AZURE_WHISPER_DEPLOYMENT_NAME: str = "whisper"
    AZURE_TRANSCRIBE_DIARIZE_DEPLOYMENT_NAME: str = "gpt-4o-transcribe-diarize"
    GPT4O_DEPLOYMENT_NAME: str = "gpt-4o-unga"
    GPT5_DEPLOYMENT_NAME: str = "gpt-5-unga"
    MODEL_ROUTER_DEPLOYMENT_NAME: str = "model-router"

    # Azure Speech Services (backup transcription)
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str = "eastus2"

    # Azure Cosmos DB
    COSMOS_ENDPOINT: Optional[str] = None
    COSMOS_KEY: Optional[str] = None
    COSMOS_DATABASE_NAME: str = "untv_analysis"
    COSMOS_SESSIONS_CONTAINER: str = "sessions"
    COSMOS_TRANSCRIPTS_CONTAINER: str = "transcripts"
    COSMOS_SPEAKERS_CONTAINER: str = "speakers"
    COSMOS_CHATS_CONTAINER: str = "chats"

    # Azure Blob Storage
    BLOB_CONNECTION_STRING: Optional[str] = None
    BLOB_CONTAINER_AUDIO: str = "audio-temp"
    BLOB_CONTAINER_TRANSCRIPTS: str = "transcripts"

    # Azure AI Search (Vector Database)
    SEARCH_ENDPOINT: Optional[str] = None
    SEARCH_API_KEY: Optional[str] = None
    SEARCH_INDEX_NAME: str = "untv-segments"

    # Processing Configuration
    TRANSCRIPTION_SERVICE: str = "gpt-4o-transcribe-diarize"  # or "azure_speech" or "whisper"
    ENTITY_MODEL: str = "gpt-4o-unga"  # Model for entity extraction
    CHAT_MODEL: str = "gpt-4o-unga"  # Model for chat interface
    EMBEDDING_MODEL: str = "text-embedding-ada-002"  # Embedding model

    # Processing Limits
    MAX_AUDIO_DURATION_HOURS: int = 6  # Maximum session duration
    MAX_CONCURRENT_PROCESSING: int = 3  # Concurrent session processing
    EMBEDDING_BATCH_SIZE: int = 100  # Batch size for embeddings

    # Temporary Storage
    TEMP_AUDIO_DIR: str = "data/audio_temp"
    TEMP_DOWNLOAD_DIR: str = "data/downloads"

    # Vector Search Configuration
    VECTOR_SEARCH_TOP_K: int = 10  # Number of segments to retrieve
    VECTOR_DIMENSION: int = 1536  # Embedding dimension

    # Chat Configuration
    CHAT_MAX_HISTORY: int = 20  # Maximum chat history to keep
    CHAT_TEMPERATURE: float = 0.7
    CHAT_MAX_TOKENS: int = 2000

    # API Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
settings = Settings()
