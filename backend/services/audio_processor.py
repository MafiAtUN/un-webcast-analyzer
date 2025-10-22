"""
Audio Processing Service
Downloads video from UN WebTV and extracts audio for transcription.
"""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp
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

    def _get_duration_sync(self, audio_path: str) -> float:
        """Synchronous helper to get audio duration using ffprobe."""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return float(result.stdout.strip())

    async def get_audio_duration(self, audio_path: str) -> int:
        """
        Get audio duration in seconds using FFmpeg.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            loop = asyncio.get_event_loop()
            duration_seconds = await loop.run_in_executor(
                None,
                self._get_duration_sync,
                audio_path
            )

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
        Validate audio file is readable and not corrupted using FFmpeg.

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

            # Validate using ffprobe
            duration = await self.get_audio_duration(audio_path)

            if duration == 0:
                logger.error(f"Audio file has no content: {audio_path}")
                return False

            logger.info(f"Audio file validated: {audio_path} ({duration}s)")
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

    async def split_audio_file(
        self,
        audio_path: str,
        chunk_duration_minutes: int = 10
    ) -> list[str]:
        """
        Split large audio file into smaller chunks for processing.

        Args:
            audio_path: Path to the audio file to split
            chunk_duration_minutes: Duration of each chunk in minutes

        Returns:
            List of paths to audio chunk files
        """
        try:
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

            # If file is small enough (<20MB), don't split it
            if file_size_mb < 20:
                logger.info(f"Audio file is small enough ({file_size_mb:.2f}MB), no splitting needed")
                return [audio_path]

            logger.info(f"Splitting large audio file ({file_size_mb:.2f}MB) into chunks")

            # Create chunks directory
            audio_file = Path(audio_path)
            chunks_dir = audio_file.parent / f"{audio_file.stem}_chunks"
            chunks_dir.mkdir(parents=True, exist_ok=True)

            # Get total duration
            duration_seconds = await self.get_audio_duration(audio_path)
            chunk_duration_seconds = chunk_duration_minutes * 60

            # Calculate number of chunks needed
            num_chunks = (duration_seconds + chunk_duration_seconds - 1) // chunk_duration_seconds

            logger.info(f"Splitting {duration_seconds}s audio into {num_chunks} chunks of {chunk_duration_minutes}min each")

            chunk_paths = []

            # Split using ffmpeg
            for i in range(num_chunks):
                start_time = i * chunk_duration_seconds
                chunk_path = chunks_dir / f"chunk_{i:03d}.mp3"

                cmd = [
                    'ffmpeg',
                    '-i', audio_path,
                    '-ss', str(start_time),
                    '-t', str(chunk_duration_seconds),
                    '-acodec', 'libmp3lame',
                    '-ab', '128k',
                    '-y',  # Overwrite output file
                    str(chunk_path)
                ]

                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True
                    )
                )

                if chunk_path.exists():
                    chunk_size_mb = chunk_path.stat().st_size / (1024 * 1024)
                    logger.info(f"Created chunk {i+1}/{num_chunks}: {chunk_path.name} ({chunk_size_mb:.2f}MB)")
                    chunk_paths.append(str(chunk_path))
                else:
                    logger.error(f"Failed to create chunk {i+1}/{num_chunks}")

            return chunk_paths

        except Exception as e:
            logger.error(f"Failed to split audio file: {str(e)}")
            # Return original file if splitting fails
            return [audio_path]

    async def cleanup_chunks(self, chunk_paths: list[str]) -> None:
        """
        Clean up audio chunk files and their directory.

        Args:
            chunk_paths: List of chunk file paths to delete
        """
        try:
            if not chunk_paths:
                return

            # Get chunks directory from first chunk path
            first_chunk = Path(chunk_paths[0])
            chunks_dir = first_chunk.parent

            # Delete all chunk files
            for chunk_path in chunk_paths:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    logger.debug(f"Deleted chunk: {chunk_path}")

            # Remove chunks directory if empty
            if chunks_dir.exists() and chunks_dir.name.endswith('_chunks'):
                try:
                    chunks_dir.rmdir()
                    logger.info(f"Removed chunks directory: {chunks_dir}")
                except OSError:
                    logger.warning(f"Chunks directory not empty: {chunks_dir}")

        except Exception as e:
            logger.error(f"Failed to cleanup chunks: {str(e)}")


# Singleton instance
audio_processor = AudioProcessor()
