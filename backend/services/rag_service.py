"""
Advanced RAG (Retrieval-Augmented Generation) Service.

Features:
- Multi-query retrieval (generate multiple search queries from user question)
- Query decomposition (break complex questions into sub-queries)
- Re-ranking and relevance scoring
- Citation tracking with timestamps
- Cross-session search
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from openai import AzureOpenAI
from config.settings import settings
from backend.services.embedding_service import embedding_service
from backend.services.vector_store import vector_store, VectorSegment
import json
import re


@dataclass
class SearchResult:
    """Represents a search result with citation information."""
    segment: VectorSegment
    similarity_score: float
    rank: int

    def to_citation(self) -> str:
        """Format as a citation string."""
        speaker = f"{self.segment.speaker_name}" if self.segment.speaker_name else "Unknown Speaker"
        country = f" ({self.segment.country})" if self.segment.country else ""
        time = f" at {self.segment.start_time}" if self.segment.start_time else ""

        return (
            f"[{self.rank}] {speaker}{country}, "
            f"'{self.segment.session_title}'{time}: "
            f'"{self.segment.text[:100]}..."'
        )


class RAGService:
    """Advanced RAG service for question answering over UN transcripts."""

    def __init__(self):
        """Initialize RAG service."""
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.chat_model = settings.CHAT_MODEL

    async def generate_multi_queries(
        self,
        user_question: str,
        num_queries: int = 3
    ) -> List[str]:
        """
        Generate multiple search queries from a single user question.

        This improves retrieval by exploring different phrasings and aspects
        of the question.

        Args:
            user_question: Original user question
            num_queries: Number of queries to generate

        Returns:
            List of search queries
        """
        system_prompt = """You are a query expansion expert for UN session transcripts.
Given a user question, generate {num_queries} different search queries that would help find relevant information.

Each query should:
1. Rephrase the question differently
2. Focus on different aspects of the question
3. Use different keywords and terminology
4. Be concise and specific

Return ONLY the queries, one per line, without numbering or extra text.""".format(num_queries=num_queries)

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ],
                temperature=0.7,
                max_tokens=200
            )

            queries_text = response.choices[0].message.content
            queries = [q.strip() for q in queries_text.strip().split('\n') if q.strip()]

            # Always include the original question
            if user_question not in queries:
                queries.insert(0, user_question)

            logger.info(f"Generated {len(queries)} search queries from: {user_question}")
            logger.debug(f"Queries: {queries}")

            return queries[:num_queries + 1]  # +1 for original

        except Exception as e:
            logger.error(f"Error generating multi-queries: {str(e)}")
            return [user_question]  # Fallback to original question

    async def decompose_query(self, complex_question: str) -> List[str]:
        """
        Decompose a complex question into simpler sub-questions.

        Example:
        "What did China and Russia say about corporate liability and did they agree?"
        -> ["What did China say about corporate liability?",
            "What did Russia say about corporate liability?",
            "Did China and Russia agree on corporate liability?"]

        Args:
            complex_question: Complex user question

        Returns:
            List of simpler sub-questions
        """
        system_prompt = """You are a question decomposition expert for UN session analysis.
Given a complex question, break it down into simpler sub-questions that, when answered together, would fully address the original question.

Rules:
1. Each sub-question should be independently answerable
2. Sub-questions should be simple and focused
3. Together, they should cover all aspects of the original question
4. Return 2-4 sub-questions maximum
5. Return ONLY the sub-questions, one per line"""

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": complex_question}
                ],
                temperature=0.3,
                max_tokens=300
            )

            questions_text = response.choices[0].message.content
            sub_questions = [q.strip() for q in questions_text.strip().split('\n') if q.strip()]

            if len(sub_questions) > 1:
                logger.info(f"Decomposed into {len(sub_questions)} sub-questions")
                logger.debug(f"Sub-questions: {sub_questions}")
                return sub_questions
            else:
                return [complex_question]

        except Exception as e:
            logger.error(f"Error decomposing query: {str(e)}")
            return [complex_question]

    async def retrieve_relevant_segments(
        self,
        question: str,
        top_k: int = 10,
        use_multi_query: bool = True,
        session_id: Optional[str] = None,
        **filters
    ) -> List[SearchResult]:
        """
        Retrieve relevant transcript segments for a question.

        Args:
            question: User question
            top_k: Number of segments to retrieve
            use_multi_query: Whether to use multi-query retrieval
            session_id: Optional session ID to limit search
            **filters: Additional filters (speaker_name, country, etc.)

        Returns:
            List of search results with citations
        """
        logger.info(f"Retrieving segments for question: {question}")

        if use_multi_query:
            # Generate multiple queries
            queries = await self.generate_multi_queries(question, num_queries=2)
        else:
            queries = [question]

        # Generate embeddings for all queries
        query_embeddings = await embedding_service.generate_embeddings_batch(queries)

        # Search with all query embeddings
        results = vector_store.search_multi_query(
            query_embeddings=query_embeddings,
            top_k=top_k,
            session_id=session_id,
            **filters
        )

        # Convert to SearchResult with rankings
        search_results = [
            SearchResult(segment=seg, similarity_score=score, rank=idx + 1)
            for idx, (seg, score) in enumerate(results)
        ]

        logger.info(f"Retrieved {len(search_results)} relevant segments")

        return search_results

    async def answer_question(
        self,
        question: str,
        session_id: Optional[str] = None,
        chat_history: Optional[List[Dict]] = None,
        top_k: int = 10,
        use_multi_query: bool = True,
        **filters
    ) -> Dict:
        """
        Answer a question using RAG.

        Args:
            question: User question
            session_id: Optional session ID to limit search
            chat_history: Previous chat messages for context
            top_k: Number of segments to retrieve
            use_multi_query: Use multi-query retrieval
            **filters: Additional filters

        Returns:
            Dict with answer, sources, and metadata
        """
        logger.info(f"Answering question: {question}")

        # Retrieve relevant segments
        search_results = await self.retrieve_relevant_segments(
            question=question,
            top_k=top_k,
            use_multi_query=use_multi_query,
            session_id=session_id,
            **filters
        )

        if not search_results:
            return {
                "answer": "I couldn't find any relevant information in the transcripts to answer this question.",
                "sources": [],
                "metadata": {
                    "segments_retrieved": 0,
                    "query_success": False
                }
            }

        # Build context from retrieved segments
        context_parts = []
        for result in search_results:
            seg = result.segment
            speaker = f"{seg.speaker_name}" if seg.speaker_name else "Unknown Speaker"
            country = f" ({seg.country})" if seg.country else ""
            time = f" [{seg.start_time}]" if seg.start_time else ""

            context_parts.append(
                f"[Source {result.rank}] {speaker}{country}{time}:\n{seg.text}"
            )

        context = "\n\n".join(context_parts)

        # Build system prompt
        system_prompt = """You are an expert analyst of UN session transcripts. Your role is to provide accurate, well-sourced answers to questions about UN sessions.

Guidelines:
1. Base your answer ONLY on the provided transcript excerpts
2. Cite your sources using [Source X] notation
3. If the information isn't in the provided excerpts, say so clearly
4. Be objective and accurate - this is for diplomatic analysis
5. Include relevant speaker names, countries, and context
6. If speakers disagree, present both perspectives
7. Quote directly when it adds value

Context from UN session transcripts:
{context}"""

        # Build chat messages
        messages = [
            {"role": "system", "content": system_prompt.format(context=context)}
        ]

        # Add chat history if provided
        if chat_history:
            messages.extend(chat_history[-6:])  # Last 6 messages for context

        # Add current question
        messages.append({"role": "user", "content": question})

        # Generate answer
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=settings.CHAT_TEMPERATURE,
                max_tokens=settings.CHAT_MAX_TOKENS
            )

            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            # Extract citations from answer
            citations = re.findall(r'\[Source (\d+)\]', answer)
            cited_sources = list(set(int(c) for c in citations))

            logger.info(f"Generated answer with {len(cited_sources)} sources cited")

            return {
                "answer": answer,
                "sources": [
                    {
                        "rank": result.rank,
                        "session_id": result.segment.session_id,
                        "session_title": result.segment.session_title,
                        "speaker_name": result.segment.speaker_name,
                        "country": result.segment.country,
                        "text": result.segment.text,
                        "start_time": result.segment.start_time,
                        "end_time": result.segment.end_time,
                        "similarity_score": round(result.similarity_score, 3),
                        "citation": result.to_citation()
                    }
                    for result in search_results
                ],
                "metadata": {
                    "segments_retrieved": len(search_results),
                    "sources_cited": len(cited_sources),
                    "tokens_used": tokens_used,
                    "query_success": True,
                    "multi_query_used": use_multi_query
                }
            }

        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            raise

    async def cross_session_analysis(
        self,
        question: str,
        session_ids: List[str],
        top_k_per_session: int = 5
    ) -> Dict:
        """
        Answer a question by comparing across multiple sessions.

        Example: "How did the US position on Article 12 evolve across sessions 3, 4, and 5?"

        Args:
            question: Comparative question
            session_ids: List of session IDs to compare
            top_k_per_session: Results per session

        Returns:
            Dict with comparative answer and sources
        """
        logger.info(f"Cross-session analysis across {len(session_ids)} sessions")

        # Get results for each session
        all_results = []
        for session_id in session_ids:
            results = await self.retrieve_relevant_segments(
                question=question,
                top_k=top_k_per_session,
                session_id=session_id,
                use_multi_query=True
            )
            all_results.extend(results)

        # Re-rank all results together
        all_results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Update rankings
        for idx, result in enumerate(all_results):
            result.rank = idx + 1

        # Generate comparative answer
        return await self.answer_question(
            question=f"{question}\n\nProvide a comparative analysis across the sessions, noting any changes or evolution in positions.",
            session_id=None,  # Already filtered
            top_k=len(all_results),  # Use all retrieved results
            use_multi_query=False  # Already done
        )


# Global RAG service instance
rag_service = RAGService()
