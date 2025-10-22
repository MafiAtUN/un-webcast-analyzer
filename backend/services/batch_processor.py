"""
Batch processor for processing multiple UN WebTV sessions in parallel.
"""
import asyncio
from typing import List, Dict, Any
from loguru import logger
from .session_processor import session_processor
from .database import db_service


class BatchProcessor:
    """Process multiple sessions in parallel with rate limiting and progress tracking."""

    def __init__(self, max_concurrent: int = 3):
        """
        Initialize batch processor.

        Args:
            max_concurrent: Maximum number of sessions to process concurrently
                           (default: 3 to respect Azure OpenAI rate limits)
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_batch(
        self,
        urls: List[str],
        progress_callback: callable = None
    ) -> Dict[str, Any]:
        """
        Process multiple UN WebTV sessions in parallel.

        Args:
            urls: List of UN WebTV URLs to process
            progress_callback: Optional callback function(completed, total, current_url)
                              for progress updates

        Returns:
            Dictionary with results for each URL
        """
        logger.info(f"Starting batch processing of {len(urls)} sessions")
        logger.info(f"Max concurrent sessions: {self.max_concurrent}")

        # Initialize database once for all sessions
        await db_service.initialize()

        results = {
            "total": len(urls),
            "completed": 0,
            "failed": 0,
            "sessions": {}
        }

        # Create tasks for all URLs
        tasks = [
            self._process_with_semaphore(url, results, progress_callback)
            for url in urls
        ]

        # Process all tasks concurrently (with semaphore limiting concurrency)
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(
            f"Batch processing complete: "
            f"{results['completed']} succeeded, {results['failed']} failed"
        )

        return results

    async def _process_with_semaphore(
        self,
        url: str,
        results: Dict[str, Any],
        progress_callback: callable = None
    ):
        """Process a single session with semaphore to limit concurrency."""
        async with self.semaphore:
            try:
                logger.info(f"🚀 Starting processing: {url}")

                # Process the session
                result = await session_processor.process_session(url)

                if result and result.get('status') == 'completed':
                    results['completed'] += 1
                    results['sessions'][url] = {
                        "status": "success",
                        "session_id": result.get('session_id'),
                        "data": result
                    }
                    logger.info(f"✅ Successfully processed: {url}")
                else:
                    results['failed'] += 1
                    results['sessions'][url] = {
                        "status": "failed",
                        "error": "Processing did not complete",
                        "data": result
                    }
                    logger.error(f"❌ Failed to process: {url}")

                # Call progress callback if provided
                if progress_callback:
                    total_processed = results['completed'] + results['failed']
                    await progress_callback(total_processed, results['total'], url)

            except Exception as e:
                results['failed'] += 1
                results['sessions'][url] = {
                    "status": "error",
                    "error": str(e)
                }
                logger.error(f"❌ Error processing {url}: {e}")

                if progress_callback:
                    total_processed = results['completed'] + results['failed']
                    await progress_callback(total_processed, results['total'], url)

    async def get_batch_status(self, session_ids: List[str]) -> Dict[str, Any]:
        """
        Get status of multiple sessions.

        Args:
            session_ids: List of session IDs to check

        Returns:
            Dictionary with status for each session
        """
        await db_service.initialize()

        statuses = {}
        for session_id in session_ids:
            try:
                session = await db_service.get_session(session_id)
                if session:
                    statuses[session_id] = {
                        "status": session.get('status'),
                        "progress": session.get('progress'),
                        "current_step": session.get('current_step'),
                        "created_at": session.get('created_at'),
                        "updated_at": session.get('updated_at')
                    }
                else:
                    statuses[session_id] = {"status": "not_found"}
            except Exception as e:
                statuses[session_id] = {"status": "error", "error": str(e)}

        return statuses


# Global batch processor instance
batch_processor = BatchProcessor(max_concurrent=3)
