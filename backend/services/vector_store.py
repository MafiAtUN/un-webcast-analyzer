"""
Vector Store Service for storing and searching transcript segments.

Features:
- In-memory vector storage (can be swapped with Azure AI Search/pgvector)
- Cosine similarity search
- Hybrid search (vector + metadata filtering)
- Persistent storage in Cosmos DB
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from loguru import logger
from datetime import datetime
import json


@dataclass
class VectorSegment:
    """Represents a transcript segment with its vector embedding."""
    id: str  # Unique ID: {session_id}_seg_{index}
    session_id: str
    session_title: str
    session_date: str
    segment_index: int
    speaker_id: Optional[str]
    speaker_name: Optional[str]
    country: Optional[str]
    text: str
    start_time: Optional[str]
    end_time: Optional[str]
    embedding: List[float]
    metadata: Dict  # Additional metadata (topics, SDGs, etc.)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class VectorStore:
    """In-memory vector store with similarity search capabilities."""

    def __init__(self):
        """Initialize empty vector store."""
        self.segments: List[VectorSegment] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self._index_dirty = True

    def add_segments(self, segments: List[VectorSegment]):
        """
        Add segments to the vector store.

        Args:
            segments: List of vector segments to add
        """
        self.segments.extend(segments)
        self._index_dirty = True
        logger.info(f"Added {len(segments)} segments to vector store")

    def add_session_segments(
        self,
        session_id: str,
        session_title: str,
        session_date: str,
        segment_data: List[Dict],
        embeddings: List[List[float]]
    ):
        """
        Add all segments from a session.

        Args:
            session_id: Session ID
            session_title: Session title
            session_date: Session date
            segment_data: List of segment dictionaries with text, speaker, times
            embeddings: List of embedding vectors
        """
        if len(segment_data) != len(embeddings):
            raise ValueError("Number of segments must match number of embeddings")

        segments = []
        for idx, (segment, embedding) in enumerate(zip(segment_data, embeddings)):
            vector_segment = VectorSegment(
                id=f"{session_id}_seg_{idx}",
                session_id=session_id,
                session_title=session_title,
                session_date=session_date,
                segment_index=idx,
                speaker_id=segment.get('speaker_id'),
                speaker_name=segment.get('speaker_name'),
                country=segment.get('country'),
                text=segment.get('text', ''),
                start_time=segment.get('start_time'),
                end_time=segment.get('end_time'),
                embedding=embedding,
                metadata=segment.get('metadata', {})
            )
            segments.append(vector_segment)

        self.add_segments(segments)
        logger.info(f"Added {len(segments)} segments from session {session_id}")

    def _build_embeddings_matrix(self):
        """Build numpy matrix of all embeddings for efficient search."""
        if not self.segments:
            self.embeddings_matrix = None
            return

        self.embeddings_matrix = np.array([s.embedding for s in self.segments])
        self._index_dirty = False
        logger.debug(f"Built embeddings matrix: shape {self.embeddings_matrix.shape}")

    def _cosine_similarity(
        self,
        query_embedding: List[float],
        top_k: int
    ) -> List[Tuple[int, float]]:
        """
        Compute cosine similarity between query and all segments.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return

        Returns:
            List of (index, similarity_score) tuples
        """
        if self._index_dirty:
            self._build_embeddings_matrix()

        if self.embeddings_matrix is None:
            return []

        # Convert query to numpy array
        query_vec = np.array(query_embedding)

        # Compute cosine similarity
        # cosine_sim = (A · B) / (||A|| * ||B||)
        dot_products = np.dot(self.embeddings_matrix, query_vec)
        query_norm = np.linalg.norm(query_vec)
        segment_norms = np.linalg.norm(self.embeddings_matrix, axis=1)
        similarities = dot_products / (segment_norms * query_norm)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_scores = similarities[top_indices]

        return list(zip(top_indices.tolist(), top_scores.tolist()))

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        session_id: Optional[str] = None,
        speaker_name: Optional[str] = None,
        country: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[Tuple[VectorSegment, float]]:
        """
        Search for similar segments.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            session_id: Optional filter by session ID
            speaker_name: Optional filter by speaker name
            country: Optional filter by country
            min_similarity: Minimum similarity score threshold

        Returns:
            List of (segment, similarity_score) tuples
        """
        if not self.segments:
            logger.warning("Vector store is empty")
            return []

        # Get similarity scores
        results = self._cosine_similarity(query_embedding, top_k * 3)  # Get more for filtering

        # Apply filters and threshold
        filtered_results = []
        for idx, score in results:
            if score < min_similarity:
                continue

            segment = self.segments[idx]

            # Apply filters
            if session_id and segment.session_id != session_id:
                continue
            if speaker_name and segment.speaker_name != speaker_name:
                continue
            if country and segment.country != country:
                continue

            filtered_results.append((segment, score))

            if len(filtered_results) >= top_k:
                break

        logger.info(
            f"Vector search returned {len(filtered_results)} results "
            f"(filters: session_id={session_id}, speaker={speaker_name}, country={country})"
        )

        return filtered_results

    def search_multi_query(
        self,
        query_embeddings: List[List[float]],
        top_k: int = 10,
        **filters
    ) -> List[Tuple[VectorSegment, float]]:
        """
        Search with multiple query embeddings and merge results.

        This is useful for multi-query retrieval where we generate multiple
        search queries from a single user question.

        Args:
            query_embeddings: List of query embedding vectors
            top_k: Number of results to return
            **filters: Additional filters

        Returns:
            List of (segment, similarity_score) tuples
        """
        # Collect results from all queries
        all_results: Dict[str, Tuple[VectorSegment, float]] = {}

        for query_emb in query_embeddings:
            results = self.search(
                query_embedding=query_emb,
                top_k=top_k,
                **filters
            )

            # Merge results, keeping highest score for each segment
            for segment, score in results:
                if segment.id not in all_results or all_results[segment.id][1] < score:
                    all_results[segment.id] = (segment, score)

        # Sort by score and return top-k
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        logger.info(f"Multi-query search returned {len(sorted_results)} unique results")

        return sorted_results

    def get_session_segments(self, session_id: str) -> List[VectorSegment]:
        """Get all segments for a session."""
        return [s for s in self.segments if s.session_id == session_id]

    def delete_session_segments(self, session_id: str):
        """Delete all segments for a session."""
        count_before = len(self.segments)
        self.segments = [s for s in self.segments if s.session_id != session_id]
        count_after = len(self.segments)
        deleted = count_before - count_after

        if deleted > 0:
            self._index_dirty = True

        logger.info(f"Deleted {deleted} segments for session {session_id}")

    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        if not self.segments:
            return {
                "total_segments": 0,
                "unique_sessions": 0,
                "embedding_dimension": 0
            }

        unique_sessions = len(set(s.session_id for s in self.segments))
        embedding_dim = len(self.segments[0].embedding) if self.segments else 0

        return {
            "total_segments": len(self.segments),
            "unique_sessions": unique_sessions,
            "embedding_dimension": embedding_dim,
            "index_status": "dirty" if self._index_dirty else "current"
        }

    def save_to_cosmos(self, container) -> int:
        """
        Save all segments to Cosmos DB.

        Args:
            container: Cosmos DB container

        Returns:
            Number of segments saved
        """
        count = 0
        for segment in self.segments:
            try:
                container.upsert_item(body=segment.to_dict())
                count += 1
            except Exception as e:
                logger.error(f"Error saving segment {segment.id}: {str(e)}")

        logger.info(f"Saved {count} segments to Cosmos DB")
        return count

    def load_from_cosmos(self, container):
        """
        Load all segments from Cosmos DB.

        Args:
            container: Cosmos DB container
        """
        try:
            query = "SELECT * FROM c"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))

            segments = []
            for item in items:
                segment = VectorSegment(**item)
                segments.append(segment)

            self.segments = segments
            self._index_dirty = True

            logger.info(f"Loaded {len(segments)} segments from Cosmos DB")

        except Exception as e:
            logger.error(f"Error loading segments from Cosmos DB: {str(e)}")
            raise


# Global vector store instance
vector_store = VectorStore()
