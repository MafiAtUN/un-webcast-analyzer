"""
Audio Processing Service
Downloads video from UN WebTV and extracts audio for transcription.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp
from pydub import AudioSegment
from loguru import logger
from config import settings


class AudioProcessor:
    """Service for downloading and processing audio from UN WebTV."""

    def __init__(self):
        """Initialize audio processor."""
        self.temp_dir = Path(settings.TEMP_AUDIO_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def download_and_extract_audio(
        self,
        video_url: str,
        session_id: str
    ) -> Optional[str]:
        """
        Download video and extract audio track.

        Args:
            video_url: UN WebTV video URL
            session_id: Session identifier

        Returns:
            Path to extracted audio file or None if failed
        """
        try:
            logger.info(f"Starting audio download for session: {session_id}")

            # Output path for audio
            audio_path = self.temp_dir / f"{session_id}.mp3"

            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.temp_dir / f"{session_id}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'extract_audio': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',  # 128 kbps - good quality, smaller size
                }],
            }

            # Download in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._download_with_ytdlp,
                video_url,
                ydl_opts
            )

            # Verify file exists
            if audio_path.exists():
                file_size_mb = audio_path.stat().st_size / (1024 * 1024)
                logger.info(
                    f"Audio downloaded successfully: {session_id} "
                    f"({file_size_mb:.2f} MB)"
                )
                return str(audio_path)
            else:
                logger.error(f"Audio file not found after download: {session_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to download audio for {session_id}: {str(e)}")
            return None

    def _download_with_ytdlp(self, url: str, options: Dict[str, Any]) -> None:
        """
        Download video using yt-dlp (synchronous).

        Args:
            url: Video URL
            options: yt-dlp options
        """
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

    async def get_audio_duration(self, audio_path: str) -> int:
        """
        Get audio duration in seconds.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(
                None,
                AudioSegment.from_file,
                audio_path
            )
            duration_seconds = len(audio) / 1000  # Convert milliseconds to seconds
            logger.info(f"Audio duration: {duration_seconds:.2f} seconds")
            return int(duration_seconds)

        except Exception as e:
            logger.error(f"Failed to get audio duration: {str(e)}")
            return 0

    async def cleanup_audio_file(self, audio_path: str) -> bool:
        """
        Delete temporary audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            True if deleted successfully
        """
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Cleaned up audio file: {audio_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to cleanup audio file: {str(e)}")
            return False

    async def validate_audio_file(self, audio_path: str) -> bool:
        """
        Validate audio file is readable and not corrupted.

        Args:
            audio_path: Path to audio file

        Returns:
            True if valid
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"Audio file does not exist: {audio_path}")
                return False

            # Check file size
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                logger.error(f"Audio file is empty: {audio_path}")
                return False

            # Try to load audio
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(
                None,
                AudioSegment.from_file,
                audio_path
            )

            if len(audio) == 0:
                logger.error(f"Audio file has no content: {audio_path}")
                return False

            logger.info(f"Audio file validated: {audio_path}")
            return True

        except Exception as e:
            logger.error(f"Audio validation failed: {str(e)}")
            return False

    def get_audio_path(self, session_id: str) -> str:
        """
        Get path for audio file.

        Args:
            session_id: Session identifier

        Returns:
            Full path to audio file
        """
        return str(self.temp_dir / f"{session_id}.mp3")


# Singleton instance
audio_processor = AudioProcessor()
