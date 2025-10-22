"""
Session Discovery Service
Discovers and lists UN WebTV sessions by date, category, and other filters.
"""
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
import asyncio


class SessionDiscovery:
    """Discover UN WebTV sessions from the website."""

    def __init__(self):
        self.base_url = "https://webtv.un.org"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    async def discover_sessions_by_date(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Discover UN WebTV sessions within a date range.

        Args:
            start_date: Start date to search from
            end_date: End date to search until
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries with metadata
        """
        logger.info(f"Discovering sessions from {start_date} to {end_date}")

        sessions = []

        try:
            # UN WebTV search/listing page (this is a mock - adjust based on actual UN WebTV structure)
            # In reality, you would need to inspect the UN WebTV website to find their listing pages
            search_url = f"{self.base_url}/en/search"

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try different approaches to discover sessions

                # Approach 1: Browse recent uploads
                recent_sessions = await self._scrape_recent_sessions(client, limit)
                sessions.extend(recent_sessions)

                # Approach 2: Search by date (if supported by website)
                # date_sessions = await self._search_by_date(client, start_date, end_date)
                # sessions.extend(date_sessions)

            # Filter by date range
            filtered_sessions = [
                s for s in sessions
                if s.get('date') and start_date <= s['date'] <= end_date
            ]

            logger.info(f"Discovered {len(filtered_sessions)} sessions in date range")
            return filtered_sessions[:limit]

        except Exception as e:
            logger.error(f"Failed to discover sessions: {e}")
            return []

    async def _scrape_recent_sessions(
        self,
        client: httpx.AsyncClient,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scrape recent sessions from UN WebTV homepage or listings.

        Note: This is a template - actual implementation depends on UN WebTV structure.
        """
        sessions = []

        try:
            # UN WebTV categories/bodies to check
            categories = [
                'general-assembly',
                'security-council',
                'human-rights-council',
                'ecosoc',
            ]

            for category in categories:
                category_url = f"{self.base_url}/en/{category}"

                try:
                    response = await client.get(category_url, headers=self.headers)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Look for video links (adjust selectors based on actual HTML)
                        video_links = soup.find_all('a', href=lambda x: x and '/asset/' in x)

                        for link in video_links[:limit]:
                            href = link.get('href')
                            if href:
                                full_url = href if href.startswith('http') else f"{self.base_url}{href}"

                                session_data = {
                                    'url': full_url,
                                    'title': link.get_text(strip=True) or 'Unknown Session',
                                    'category': category.replace('-', ' ').title(),
                                    'discovered_at': datetime.now(),
                                }

                                # Extract session ID from URL
                                import re
                                match = re.search(r'/asset/[^/]+/([a-z0-9]+)', full_url)
                                if match:
                                    session_data['session_id'] = match.group(1)
                                    sessions.append(session_data)

                except Exception as e:
                    logger.warning(f"Failed to scrape category {category}: {e}")
                    continue

                if len(sessions) >= limit:
                    break

        except Exception as e:
            logger.error(f"Failed to scrape recent sessions: {e}")

        return sessions

    async def get_sessions_by_body(
        self,
        body: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get sessions from a specific UN body.

        Args:
            body: UN body name (e.g., 'security-council', 'general-assembly')
            limit: Maximum sessions to return

        Returns:
            List of session dictionaries
        """
        logger.info(f"Getting sessions for body: {body}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await self._scrape_body_sessions(client, body, limit)
        except Exception as e:
            logger.error(f"Failed to get sessions for {body}: {e}")
            return []

    async def _scrape_body_sessions(
        self,
        client: httpx.AsyncClient,
        body: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Scrape sessions from a specific UN body page."""
        sessions = []

        body_url = f"{self.base_url}/en/{body}"

        try:
            response = await client.get(body_url, headers=self.headers)
            if response.status_code != 200:
                return sessions

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all video/session links
            links = soup.find_all('a', href=lambda x: x and '/asset/' in x)

            for link in links[:limit]:
                href = link.get('href')
                if not href:
                    continue

                full_url = href if href.startswith('http') else f"{self.base_url}{href}"

                # Extract metadata from link
                import re
                match = re.search(r'/asset/[^/]+/([a-z0-9]+)', full_url)
                if not match:
                    continue

                session_id = match.group(1)
                title = link.get_text(strip=True) or 'Unknown Session'

                sessions.append({
                    'session_id': session_id,
                    'url': full_url,
                    'title': title,
                    'body': body.replace('-', ' ').title(),
                    'discovered_at': datetime.now(),
                })

        except Exception as e:
            logger.error(f"Failed to scrape {body}: {e}")

        return sessions

    def get_sample_sessions(self) -> List[Dict[str, Any]]:
        """
        Get sample/known UN WebTV sessions for demonstration.

        Returns:
            List of sample session dictionaries
        """
        # These are real UN WebTV URLs for demonstration
        sample_sessions = [
            {
                'session_id': 'k1251fzd6n',
                'url': 'https://webtv.un.org/en/asset/k12/k1251fzd6n',
                'title': 'Security Council Meeting - Sample',
                'date': datetime.now() - timedelta(days=1),
                'body': 'Security Council',
                'duration_est': '3 hours',
            },
            {
                'session_id': 'k1y7kgo2oc',
                'url': 'https://webtv.un.org/en/asset/k1y/k1y7kgo2oc',
                'title': 'UNCTAD 16 Media Briefing',
                'date': datetime.now() - timedelta(days=2),
                'body': 'UNCTAD',
                'duration_est': '18 minutes',
            },
            {
                'session_id': 'k18073190m',
                'url': 'https://webtv.un.org/en/asset/k18/k18073190m',
                'title': 'General Assembly Session - Sample',
                'date': datetime.now() - timedelta(days=3),
                'body': 'General Assembly',
                'duration_est': '2 hours',
            },
        ]

        return sample_sessions


# Singleton instance
session_discovery = SessionDiscovery()
