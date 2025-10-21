"""
UN WebTV Scraper Service
Extracts metadata and video information from UN WebTV pages.
"""

import re
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger


class UNTVScraper:
    """Scraper for UN WebTV sessions."""

    def __init__(self):
        self.base_url = "https://webtv.un.org"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def extract_entry_id(self, url: str) -> Optional[str]:
        """
        Extract Kaltura Entry ID from UN WebTV URL.

        Args:
            url: UN WebTV URL (e.g., https://webtv.un.org/en/asset/k1b/k1baa85czq)

        Returns:
            Entry ID (e.g., k1baa85czq) or None if invalid
        """
        # Pattern: /asset/{category}/{entry_id}
        pattern = r'/asset/[^/]+/([a-z0-9]+)'
        match = re.search(pattern, url)

        if match:
            return match.group(1)

        logger.warning(f"Could not extract entry ID from URL: {url}")
        return None

    async def scrape_session_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape metadata from UN WebTV session page.

        Args:
            url: UN WebTV session URL

        Returns:
            Dictionary with session metadata or None if failed
        """
        entry_id = self.extract_entry_id(url)
        if not entry_id:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            metadata = {
                "id": entry_id,
                "url": url,
                "kaltura_entry_id": self._extract_kaltura_id(soup, response.text),
                "title": self._extract_title(soup),
                "date": self._extract_date(soup),
                "duration_seconds": self._extract_duration(soup),
                "session_type": self._extract_session_type(soup),
                "broadcasting_entity": self._extract_entity(soup),
                "location": self._extract_location(soup),
                "languages": self._extract_languages(soup),
                "categories": self._extract_categories(soup),
                "description": self._extract_description(soup),
            }

            logger.info(f"Successfully scraped metadata for session: {entry_id}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to scrape session {url}: {str(e)}")
            return None

    def _extract_kaltura_id(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract Kaltura media ID from page source."""
        # Look for Kaltura player configuration
        pattern = r"'entryId':\s*'([^']+)'"
        match = re.search(pattern, html)
        if match:
            return match.group(1)

        # Alternative pattern
        pattern = r'"entry_id":\s*"([^"]+)"'
        match = re.search(pattern, html)
        return match.group(1) if match else None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract session title."""
        # Try meta og:title first
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title['content'].strip()

        # Try h1 tag
        h1 = soup.find('h1')
        if h1:
            return h1.text.strip()

        # Try title tag
        title = soup.find('title')
        if title:
            return title.text.strip()

        return "Unknown Session"

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract session date."""
        # Look for date in various formats
        date_patterns = [
            r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})',  # "21 October 2025"
            r'(\d{4}-\d{2}-\d{2})',  # "2025-10-21"
        ]

        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                try:
                    # Try parsing different formats
                    for fmt in ['%d %B %Y', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass

        return None

    def _extract_duration(self, soup: BeautifulSoup) -> int:
        """Extract session duration in seconds."""
        # Look for duration in format HH:MM:SS or MM:SS
        duration_pattern = r'(\d{1,2}):(\d{2}):(\d{2})'
        text = soup.get_text()
        match = re.search(duration_pattern, text)

        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            return hours * 3600 + minutes * 60 + seconds

        return 0

    def _extract_session_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract session type (e.g., 'Intergovernmental Working Group')."""
        title = self._extract_title(soup)
        # Extract from title pattern
        if 'Working Group' in title:
            return 'Intergovernmental Working Group'
        elif 'General Assembly' in title:
            return 'General Assembly'
        elif 'Security Council' in title:
            return 'Security Council'
        elif 'Human Rights Council' in title:
            return 'Human Rights Council'
        return None

    def _extract_entity(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract broadcasting entity (UNOG, UNHQ, etc.)."""
        text = soup.get_text()
        if 'Geneva' in text or 'UNOG' in text:
            return 'UNOG'
        elif 'New York' in text or 'UNHQ' in text:
            return 'UNHQ'
        return None

    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract meeting location."""
        # Look for room information
        room_pattern = r'Room\s+([IVX]+|\d+)'
        text = soup.get_text()
        match = re.search(room_pattern, text)
        if match:
            return f"Room {match.group(1)}"
        return None

    def _extract_languages(self, soup: BeautifulSoup) -> list:
        """Extract available languages."""
        # Common UN languages
        languages = []
        text = soup.get_text().lower()
        lang_keywords = {
            'arabic': 'ar',
            'chinese': 'zh',
            'english': 'en',
            'french': 'fr',
            'russian': 'ru',
            'spanish': 'es'
        }

        for keyword, code in lang_keywords.items():
            if keyword in text:
                languages.append(code)

        return languages if languages else ['en']

    def _extract_categories(self, soup: BeautifulSoup) -> list:
        """Extract session categories/tags."""
        categories = []

        # Look for keywords in title and description
        text = soup.get_text().lower()

        keywords_map = {
            'human rights': 'Human Rights',
            'business': 'Business',
            'development': 'Development',
            'peace': 'Peace & Security',
            'climate': 'Climate',
            'health': 'Health',
        }

        for keyword, category in keywords_map.items():
            if keyword in text:
                categories.append(category)

        return categories

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract session description."""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()

        # Try og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()

        return None


# Singleton instance
scraper = UNTVScraper()
