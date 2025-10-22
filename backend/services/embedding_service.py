"""
Embedding Service for generating and caching text embeddings.

Features:
- Batch embedding generation
- In-memory caching to reduce API calls
- Support for multiple embedding models
- Cost tracking
"""

import hashlib
from typing import List, Dict, Optional
from loguru import logger
from openai import AzureOpenAI
from config.settings import settings
import time


class EmbeddingService:
    """Service for generating and managing text embeddings."""

    def __init__(self):
        """Initialize the embedding service with Azure OpenAI client."""
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.model = settings.EMBEDDING_MODEL
        self.embedding_cache: Dict[str, List[float]] = {}  # In-memory cache
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_tokens_used = 0

    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for the text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            use_cache: Whether to use cache

        Returns:
            Embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self.embedding_cache:
                self.cache_hits += 1
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return self.embedding_cache[cache_key]
            self.cache_misses += 1

        # Generate embedding
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )

            embedding = response.data[0].embedding
            self.total_tokens_used += response.usage.total_tokens

            # Cache the result
            if use_cache:
                self.embedding_cache[cache_key] = embedding

            logger.debug(
                f"Generated embedding for text: {text[:50]}... "
                f"(dimension: {len(embedding)})"
            )

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
        batch_size: int = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            use_cache: Whether to use cache
            batch_size: Batch size (default from settings)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        embeddings = []

        logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size}")

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_start = time.time()

            # Check cache first
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []

            for idx, text in enumerate(batch):
                if use_cache:
                    cache_key = self._get_cache_key(text)
                    if cache_key in self.embedding_cache:
                        cached_embeddings.append((idx, self.embedding_cache[cache_key]))
                        self.cache_hits += 1
                        continue

                uncached_texts.append(text)
                uncached_indices.append(idx)
                if use_cache:
                    self.cache_misses += 1

            # Generate embeddings for uncached texts
            new_embeddings = []
            if uncached_texts:
                try:
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=uncached_texts
                    )

                    new_embeddings = [item.embedding for item in response.data]
                    self.total_tokens_used += response.usage.total_tokens

                    # Cache new embeddings
                    if use_cache:
                        for text, embedding in zip(uncached_texts, new_embeddings):
                            cache_key = self._get_cache_key(text)
                            self.embedding_cache[cache_key] = embedding

                except Exception as e:
                    logger.error(f"Error in batch embedding generation: {str(e)}")
                    raise

            # Combine cached and new embeddings in correct order
            batch_embeddings = [None] * len(batch)
            for idx, embedding in cached_embeddings:
                batch_embeddings[idx] = embedding
            for idx, embedding in zip(uncached_indices, new_embeddings):
                batch_embeddings[idx] = embedding

            embeddings.extend(batch_embeddings)

            batch_time = time.time() - batch_start
            logger.info(
                f"Batch {i // batch_size + 1}: Generated {len(uncached_texts)} new, "
                f"retrieved {len(cached_embeddings)} cached embeddings in {batch_time:.2f}s"
            )

        logger.info(
            f"Embedding generation complete. "
            f"Cache hits: {self.cache_hits}, misses: {self.cache_misses}, "
            f"total tokens: {self.total_tokens_used}"
        )

        return embeddings

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0

        return {
            "cache_size": len(self.embedding_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_tokens_used": self.total_tokens_used
        }

    def clear_cache(self):
        """Clear the embedding cache."""
        cache_size = len(self.embedding_cache)
        self.embedding_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info(f"Cleared embedding cache ({cache_size} entries)")


# Global embedding service instance
embedding_service = EmbeddingService()
