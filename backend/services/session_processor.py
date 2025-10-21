"""
Session Processing Orchestrator
Coordinates the entire workflow of processing a UN WebTV session.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from backend.models.session import (
    SessionMetadata,
    Transcript,
    TranscriptSegment,
    ProcessingProgress,
    EntityExtraction
)
from backend.services.untv_scraper import scraper
from backend.services.audio_processor import audio_processor
from backend.services.azure_openai_client import azure_openai_client
from backend.services.database import db_service


class SessionProcessor:
    """Orchestrates the processing of UN WebTV sessions."""

    async def process_session(
        self,
        url: str,
        user_id: Optional[str] = None
    ) -> Optional[SessionMetadata]:
        """
        Process a complete UN WebTV session.

        Args:
            url: UN WebTV session URL
            user_id: Optional user identifier

        Returns:
            Processed session metadata or None if failed
        """
        session_id = None
        audio_path = None

        try:
            # Step 1: Extract session ID and check if already processed
            logger.info(f"Starting session processing: {url}")
            session_id = scraper.extract_entry_id(url)

            if not session_id:
                logger.error(f"Invalid UN WebTV URL: {url}")
                return None

            # Check if session already exists
            existing_session = await db_service.get_session(session_id)
            if existing_session:
                logger.info(f"Session already processed: {session_id}")
                return existing_session

            # Step 2: Scrape session metadata
            await self._update_progress(
                session_id,
                "downloading",
                10,
                "Extracting session metadata"
            )

            metadata = await scraper.scrape_session_metadata(url)
            if not metadata:
                logger.error(f"Failed to scrape metadata: {url}")
                return None

            # Create session record
            session = SessionMetadata(
                **metadata,
                processing_status="processing",
                created_by=user_id
            )
            await db_service.create_session(session)

            # Step 3: Download and extract audio
            await self._update_progress(
                session_id,
                "downloading",
                20,
                "Downloading audio from UN WebTV"
            )

            audio_path = await audio_processor.download_and_extract_audio(
                url,
                session_id
            )

            if not audio_path:
                await self._mark_failed(session_id, "Failed to download audio")
                return None

            # Validate audio
            if not await audio_processor.validate_audio_file(audio_path):
                await self._mark_failed(session_id, "Audio file validation failed")
                return None

            # Step 4: Transcribe with speaker diarization
            await self._update_progress(
                session_id,
                "transcribing",
                40,
                "Transcribing audio with speaker identification"
            )

            transcription_result = await azure_openai_client.transcribe_audio_with_diarization(
                audio_path,
                language=metadata.get("languages", ["en"])[0]
            )

            if not transcription_result:
                await self._mark_failed(session_id, "Transcription failed")
                return None

            # Save transcript
            transcript = Transcript(
                id=f"{session_id}_transcript",
                session_id=session_id,
                full_text=transcription_result["full_text"],
                segments=[
                    TranscriptSegment(**seg)
                    for seg in transcription_result["segments"]
                ],
                word_count=len(transcription_result["full_text"].split()),
                speaker_count=len(set(
                    seg["speaker_id"]
                    for seg in transcription_result["segments"]
                )),
                language=transcription_result.get("language", "en")
            )

            await db_service.create_transcript(transcript)

            # Step 5: Extract entities
            await self._update_progress(
                session_id,
                "extracting",
                60,
                "Extracting entities (speakers, countries, SDGs, topics)"
            )

            entities_raw = await azure_openai_client.extract_entities(
                transcription_result["full_text"],
                session.title
            )

            entities = self._parse_entities(entities_raw)

            # Step 6: Generate summary
            await self._update_progress(
                session_id,
                "extracting",
                75,
                "Generating executive summary"
            )

            summary = await azure_openai_client.generate_summary(
                transcription_result["full_text"],
                session.title,
                entities_raw
            )

            # Step 7: Generate embeddings (for future vector search)
            await self._update_progress(
                session_id,
                "embedding",
                85,
                "Generating embeddings for semantic search"
            )

            # Create text chunks for embedding
            segment_texts = [seg.text for seg in transcript.segments]
            embeddings = await azure_openai_client.generate_embeddings(segment_texts)

            logger.info(f"Generated {len(embeddings)} embeddings")

            # TODO: Store embeddings in vector database (Azure AI Search)
            # This will be implemented when AI Search is ready

            # Step 8: Update session with results
            await self._update_progress(
                session_id,
                "completed",
                95,
                "Finalizing session data"
            )

            session.entities = entities
            session.summary = summary
            session.processing_status = "completed"
            session.processed_date = datetime.utcnow()

            await db_service.update_session(session)

            # Step 9: Cleanup
            await self._update_progress(
                session_id,
                "completed",
                100,
                "Processing complete"
            )

            if audio_path:
                await audio_processor.cleanup_audio_file(audio_path)

            logger.info(f"Session processing completed: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Session processing failed: {str(e)}")
            if session_id:
                await self._mark_failed(session_id, str(e))

            # Cleanup on error
            if audio_path:
                await audio_processor.cleanup_audio_file(audio_path)

            return None

    def _parse_entities(self, raw_entities: Dict[str, Any]) -> EntityExtraction:
        """
        Parse raw entity extraction results into structured format.

        Args:
            raw_entities: Raw entities from LLM

        Returns:
            Structured entity extraction
        """
        try:
            # The LLM returns JSON, convert to our model
            return EntityExtraction(
                speakers=raw_entities.get("speakers", []),
                countries=raw_entities.get("countries", []),
                sdgs=raw_entities.get("sdgs", []),
                topics=raw_entities.get("topics", []),
                organizations=raw_entities.get("organizations", []),
                treaties=raw_entities.get("treaties", []),
                key_decisions=raw_entities.get("key_decisions", []),
                interventions_by_country=raw_entities.get("interventions_by_country", {})
            )

        except Exception as e:
            logger.error(f"Failed to parse entities: {str(e)}")
            return EntityExtraction()

    async def _update_progress(
        self,
        session_id: str,
        status: str,
        progress: int,
        message: str
    ) -> None:
        """
        Update processing progress (for future WebSocket updates).

        Args:
            session_id: Session identifier
            status: Current status
            progress: Progress percentage (0-100)
            message: Progress message
        """
        logger.info(f"[{session_id}] {progress}% - {message}")
        # TODO: Broadcast via WebSocket for real-time updates

    async def _mark_failed(self, session_id: str, error: str) -> None:
        """
        Mark session as failed.

        Args:
            session_id: Session identifier
            error: Error message
        """
        try:
            session = await db_service.get_session(session_id)
            if session:
                session.processing_status = "failed"
                session.error_message = error
                await db_service.update_session(session)

        except Exception as e:
            logger.error(f"Failed to mark session as failed: {str(e)}")


# Singleton instance
session_processor = SessionProcessor()
