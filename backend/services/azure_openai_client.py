"""
Azure OpenAI Client Service
Handles all interactions with Azure OpenAI services including transcription,
entity extraction, embeddings, and chat.
"""

from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from loguru import logger
from config import settings
import time
import asyncio


class AzureOpenAIClient:
    """Client for Azure OpenAI services."""

    def __init__(self):
        """Initialize Azure OpenAI client."""
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )

    async def transcribe_audio_with_diarization(
        self,
        audio_file_path: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Transcribe audio with speaker diarization using GPT-4o-transcribe-diarize.
        Handles large files by splitting them into chunks.

        Args:
            audio_file_path: Path to audio file
            language: Audio language code

        Returns:
            Dictionary with transcript segments and speaker information
        """
        from backend.services.audio_processor import audio_processor

        try:
            # Split large audio files into chunks
            chunk_paths = await audio_processor.split_audio_file(audio_file_path)

            if len(chunk_paths) == 1:
                # Single file, transcribe normally
                return await self._transcribe_single_file(chunk_paths[0], language)
            else:
                # Multiple chunks, transcribe each and merge
                logger.info(f"Transcribing {len(chunk_paths)} audio chunks")
                all_segments = []
                cumulative_time_offset = 0.0

                for idx, chunk_path in enumerate(chunk_paths):
                    logger.info(f"Transcribing chunk {idx + 1}/{len(chunk_paths)}")

                    chunk_result = await self._transcribe_single_file(chunk_path, language)

                    # Adjust timestamps for chunks after the first one
                    if 'segments' in chunk_result:
                        for segment in chunk_result['segments']:
                            segment['start'] += cumulative_time_offset
                            segment['end'] += cumulative_time_offset
                        all_segments.extend(chunk_result['segments'])

                    # Update time offset for next chunk (10 minutes per chunk)
                    cumulative_time_offset += 600.0

                # Clean up chunks
                await audio_processor.cleanup_chunks(chunk_paths)

                # Merge results
                merged_result = {
                    'full_text': ' '.join([s.get('text', '') for s in all_segments]),
                    'segments': all_segments,
                    'language': 'en',
                    'duration': cumulative_time_offset
                }

                logger.info(f"Merged transcription from {len(chunk_paths)} chunks, total segments: {len(all_segments)}")
                return merged_result

        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise

    async def _transcribe_single_file(
        self,
        audio_file_path: str,
        language: str = "en",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Transcribe a single audio file with retry logic.

        Args:
            audio_file_path: Path to audio file
            language: Language code
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary with transcript segments
        """
        retry_delays = [10, 30, 60]  # Seconds to wait between retries

        for attempt in range(max_retries):
            try:
                with open(audio_file_path, "rb") as audio_file:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt + 1}/{max_retries} for: {audio_file_path}")
                    else:
                        logger.info(f"Starting transcription for: {audio_file_path}")

                    # Using the gpt-4o-transcribe-diarize deployment
                    result = self.client.audio.transcriptions.create(
                        model=settings.AZURE_TRANSCRIBE_DIARIZE_DEPLOYMENT_NAME,
                        file=audio_file,
                        language=language,
                        response_format="diarized_json",
                        chunking_strategy="auto"
                    )

                    logger.info("Transcription completed successfully")
                    return self._parse_transcription_result(result)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Transcription attempt {attempt + 1} failed: {error_msg}")

                # Check if this is a server error (500) or rate limit that we should retry
                should_retry = (
                    "500" in error_msg or
                    "server_error" in error_msg or
                    "429" in error_msg or
                    "rate_limit" in error_msg.lower()
                )

                if should_retry and attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {max_retries} attempts failed for: {audio_file_path}")
                    raise

    def _parse_transcription_result(self, result: Any) -> Dict[str, Any]:
        """Parse transcription result from diarized_json format into structured format."""
        segments = []

        if hasattr(result, 'segments'):
            for idx, segment in enumerate(result.segments):
                # diarized_json format has 'speaker' attribute with values like "A", "B", etc.
                speaker_label = getattr(segment, 'speaker', f"SPEAKER_{idx % 5 + 1}")

                segments.append({
                    "segment_index": idx,
                    "speaker_id": f"SPEAKER_{speaker_label}",  # Convert "A" to "SPEAKER_A"
                    "start_time": self._format_time(segment.start),
                    "end_time": self._format_time(segment.end),
                    "text": segment.text.strip(),
                    "confidence": getattr(segment, 'confidence', 1.0)
                })

        return {
            "full_text": result.text,
            "segments": segments,
            "language": getattr(result, 'language', 'en'),
            "duration": getattr(result, 'duration', 0) if hasattr(result, 'duration') and result.duration else 0
        }

    def _format_time(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    async def extract_entities(
        self,
        transcript_text: str,
        session_title: str
    ) -> Dict[str, Any]:
        """
        Extract entities from transcript using GPT-4o with structured output.

        Args:
            transcript_text: Full transcript text
            session_title: Session title for context

        Returns:
            Dictionary with extracted entities
        """
        try:
            logger.info("Starting entity extraction")

            system_prompt = """You are an expert analyst of United Nations proceedings.
Extract the following information from the provided UN session transcript:

1. Speakers: Name, country, role, organization
2. Countries mentioned or represented
3. SDGs (Sustainable Development Goals 1-17) mentioned with context
4. Main topics and themes discussed
5. Organizations and institutions mentioned
6. Treaties, conventions, or legal instruments referenced
7. Key decisions or outcomes
8. Number of interventions by each country

Provide structured JSON output with high accuracy."""

            user_prompt = f"""Session Title: {session_title}

Transcript:
{transcript_text[:15000]}  # Limit to avoid token limits

Extract all relevant entities and provide detailed analysis."""

            response = self.client.chat.completions.create(
                model=settings.ENTITY_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4000
            )

            import json
            entities = json.loads(response.choices[0].message.content)

            logger.info("Entity extraction completed")
            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            raise

    async def generate_summary(
        self,
        transcript_text: str,
        session_title: str,
        entities: Dict[str, Any]
    ) -> str:
        """
        Generate executive summary of the session.

        Args:
            transcript_text: Full transcript
            session_title: Session title
            entities: Extracted entities

        Returns:
            Executive summary text
        """
        try:
            logger.info("Generating session summary")

            prompt = f"""Provide a concise executive summary (200-300 words) of this UN session:

Title: {session_title}

Key Participants: {', '.join(entities.get('countries', [])[:10])}
Main Topics: {', '.join(entities.get('topics', [])[:5])}

Transcript Preview:
{transcript_text[:5000]}

Summary should cover:
1. Main discussion points
2. Key positions/statements
3. Outcomes or decisions
4. Notable interventions
"""

            response = self.client.chat.completions.create(
                model=settings.GPT4O_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=500
            )

            summary = response.choices[0].message.content.strip()
            logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            raise

    async def generate_embeddings(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for text segments.

        Args:
            texts: List of text segments to embed

        Returns:
            List of embedding vectors
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} segments")

            # Process in batches to avoid rate limits
            batch_size = settings.EMBEDDING_BATCH_SIZE
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                response = self.client.embeddings.create(
                    model=settings.EMBEDDING_MODEL,
                    input=batch
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            logger.info(f"Generated {len(all_embeddings)} embeddings")
            return all_embeddings

        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        context_segments: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate chat completion with optional RAG context.

        Args:
            messages: Chat messages history
            context_segments: Retrieved context segments for RAG
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Response with message and metadata
        """
        try:
            # Add context to system message if provided
            enhanced_messages = messages.copy()

            if context_segments:
                context_text = "\n\n---\n\n".join(context_segments)
                system_msg = {
                    "role": "system",
                    "content": f"""You are an AI assistant helping analyze UN session transcripts.
Use the following context from the session to answer questions accurately.
Always cite specific segments when making claims.

Context:
{context_text}
"""
                }
                enhanced_messages.insert(0, system_msg)

            response = self.client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=enhanced_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return {
                "message": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "finish_reason": response.choices[0].finish_reason
            }

        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            raise


# Singleton instance
azure_openai_client = AzureOpenAIClient()
