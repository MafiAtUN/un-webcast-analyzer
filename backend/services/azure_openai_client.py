"""
Azure OpenAI Client Service
Handles all interactions with Azure OpenAI services including transcription,
entity extraction, embeddings, and chat.
"""

from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from loguru import logger
from config import settings


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

        Args:
            audio_file_path: Path to audio file
            language: Audio language code

        Returns:
            Dictionary with transcript segments and speaker information
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                logger.info(f"Starting transcription for: {audio_file_path}")

                # Using the gpt-4o-transcribe-diarize deployment
                result = self.client.audio.transcriptions.create(
                    model=settings.AZURE_TRANSCRIBE_DIARIZE_DEPLOYMENT_NAME,
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )

                logger.info("Transcription completed successfully")
                return self._parse_transcription_result(result)

        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise

    def _parse_transcription_result(self, result: Any) -> Dict[str, Any]:
        """Parse transcription result into structured format."""
        segments = []

        if hasattr(result, 'segments'):
            for idx, segment in enumerate(result.segments):
                segments.append({
                    "segment_index": idx,
                    "speaker_id": getattr(segment, 'speaker', f"SPEAKER_{idx % 5 + 1}"),
                    "start_time": self._format_time(segment.start),
                    "end_time": self._format_time(segment.end),
                    "text": segment.text.strip(),
                    "confidence": getattr(segment, 'confidence', 1.0)
                })

        return {
            "full_text": result.text,
            "segments": segments,
            "language": getattr(result, 'language', 'en'),
            "duration": getattr(result, 'duration', 0)
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
