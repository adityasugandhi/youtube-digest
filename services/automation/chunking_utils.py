"""
Transcript chunking utilities for hierarchical vector storage
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TranscriptChunk:
    """Individual transcript chunk with metadata"""

    text: str
    start_ms: int
    end_ms: int
    duration_ms: int
    chunk_index: int
    lang: Optional[str] = None


class TranscriptChunker:
    """Handles transcript chunking with various strategies"""

    def __init__(
        self, min_words: int = 120, max_words: int = 300, overlap_words: int = 20
    ):
        self.min_words = min_words
        self.max_words = max_words
        self.overlap_words = overlap_words

    def word_count(self, text: str) -> int:
        """Count words in text"""
        return len((text or "").split())

    def chunk_supadata_transcript(self, transcript_data) -> List[TranscriptChunk]:
        """
        Chunk Supadata transcript response into meaningful segments

        Args:
            transcript_data: Supadata API response (dict or Transcript object)

        Returns:
            List of TranscriptChunk objects
        """
        chunks = []

        # Handle both dict and Transcript object formats
        if hasattr(transcript_data, "content"):
            # Supadata Transcript object
            content = transcript_data.content
            lang = transcript_data.lang if hasattr(transcript_data, "lang") else "en"
        else:
            # Dict format
            content = transcript_data.get("content", [])
            lang = transcript_data.get("lang", "en")

        if isinstance(content, str):
            # Handle plain text response
            return self._chunk_plain_text(content, lang)

        if not content or not isinstance(content, list):
            logger.warning("No content found in transcript data")
            return []

        # Merge small segments and create meaningful chunks
        merged_segments = self._merge_small_segments(content)

        # Convert to TranscriptChunk objects
        for i, segment in enumerate(merged_segments):
            # Handle both dict and object formats
            if hasattr(segment, "text"):
                # TranscriptChunk object
                text = segment.text
                offset = segment.offset
                duration = segment.duration
                segment_lang = segment.lang if hasattr(segment, "lang") else lang
            else:
                # Dict format
                text = segment.get("text", "")
                offset = segment.get("offset", 0)
                duration = segment.get("duration", 0)
                segment_lang = segment.get("lang", lang)

            chunk = TranscriptChunk(
                text=text,
                start_ms=int(offset),
                end_ms=int(offset) + int(duration),
                duration_ms=int(duration),
                chunk_index=i,
                lang=segment_lang,
            )
            chunks.append(chunk)

        logger.info(
            f"Created {len(chunks)} chunks from {len(content)} original segments"
        )
        return chunks

    def _chunk_plain_text(
        self, text: str, lang: Optional[str] = None
    ) -> List[TranscriptChunk]:
        """Chunk plain text into segments"""
        words = text.split()
        chunks = []

        if not words:
            return chunks

        chunk_index = 0
        start_word = 0

        while start_word < len(words):
            # Determine chunk end
            end_word = min(start_word + self.max_words, len(words))

            # Try to break at sentence boundaries if possible
            chunk_words = words[start_word:end_word]
            chunk_text = " ".join(chunk_words)

            # Estimate timing (rough approximation: 150 words per minute)
            words_per_ms = 150 / (60 * 1000)  # words per millisecond
            start_ms = int(start_word / words_per_ms) if start_word > 0 else 0
            duration_ms = int(len(chunk_words) / words_per_ms)
            end_ms = start_ms + duration_ms

            chunk = TranscriptChunk(
                text=chunk_text,
                start_ms=start_ms,
                end_ms=end_ms,
                duration_ms=duration_ms,
                chunk_index=chunk_index,
                lang=lang,
            )
            chunks.append(chunk)

            # Move to next chunk with overlap
            start_word = max(start_word + self.max_words - self.overlap_words, end_word)
            chunk_index += 1

        return chunks

    def _merge_small_segments(
        self, segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge small transcript segments into meaningful chunks"""
        if not segments:
            return []

        merged = []
        current_buffer = []
        current_word_count = 0

        for segment in segments:
            # Handle both dict and object formats
            if hasattr(segment, "text"):
                text = segment.text
            else:
                text = segment.get("text", "")
            word_count = self.word_count(text)

            current_buffer.append(segment)
            current_word_count += word_count

            # If we've reached minimum words or this is a natural break
            if (
                current_word_count >= self.min_words
                or current_word_count >= self.max_words
                or self._is_natural_break(text)
            ):

                merged_segment = self._merge_buffer(current_buffer)
                merged.append(merged_segment)

                # Reset buffer
                current_buffer = []
                current_word_count = 0

        # Handle remaining buffer
        if current_buffer:
            merged_segment = self._merge_buffer(current_buffer)
            merged.append(merged_segment)

        return merged

    def _merge_buffer(self, buffer: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a buffer of segments into a single segment"""
        if not buffer:
            return {}

        if len(buffer) == 1:
            return buffer[0]

        # Merge text - handle both dict and object formats
        merged_texts = []
        for seg in buffer:
            if hasattr(seg, "text"):
                merged_texts.append(seg.text)
            else:
                merged_texts.append(seg.get("text", ""))
        merged_text = " ".join(merged_texts)

        # Calculate timing - handle both formats
        first_seg = buffer[0]
        last_seg = buffer[-1]

        if hasattr(first_seg, "offset"):
            start_offset = int(first_seg.offset)
            end_offset = int(last_seg.offset) + int(last_seg.duration)
            lang = first_seg.lang if hasattr(first_seg, "lang") else "en"
        else:
            start_offset = int(first_seg.get("offset", 0))
            end_offset = int(last_seg.get("offset", 0)) + int(
                last_seg.get("duration", 0)
            )
            lang = first_seg.get("lang", "en")

        duration = end_offset - start_offset

        return {
            "text": merged_text,
            "offset": start_offset,
            "duration": duration,
            "lang": lang,
        }

    def _is_natural_break(self, text: str) -> bool:
        """Check if text ends with a natural break (sentence ending)"""
        text = text.strip()
        if not text:
            return False

        # Check for sentence endings
        sentence_endings = [".", "!", "?", "...", "—", "–"]
        return any(text.endswith(ending) for ending in sentence_endings)


class ChunkMetadataBuilder:
    """Builds metadata for transcript chunks"""

    @staticmethod
    def build_chunk_payload(
        chunk: TranscriptChunk,
        channel_id: str,
        channel_name: str,
        video_id: str,
        video_title: str,
        video_url: str,
        publish_time: str,
        presenters: List[str] = None,
        category: str = "general",
    ) -> Dict[str, Any]:
        """Build payload for a transcript chunk"""

        # Create hierarchical ID for internal reference
        hierarchical_id = f"{channel_id}:{video_id}:{chunk.chunk_index:04d}"

        return {
            # Hierarchy identifiers
            "channel_id": channel_id,
            "channel_name": channel_name,
            "video_id": video_id,
            "video_title": video_title,
            "video_url": video_url,
            "hierarchical_id": hierarchical_id,  # For filtering and reference
            # Chunk-specific data
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.text,
            "start_ms": chunk.start_ms,
            "end_ms": chunk.end_ms,
            "duration_ms": chunk.duration_ms,
            "lang": chunk.lang or "en",
            # Additional metadata
            "presenters": presenters or [],
            "category": category,
            "publish_time": publish_time,
            "type": "transcript_chunk",
            "created_at": datetime.utcnow().isoformat(),
            # Searchable fields
            "word_count": len(chunk.text.split()),
            "has_speech": bool(chunk.text.strip()),
            # YouTube URL with timestamp
            "timestamped_url": (
                f"{video_url}&t={chunk.start_ms // 1000}s"
                if chunk.start_ms > 0
                else video_url
            ),
        }

    @staticmethod
    def build_hierarchical_id(channel_id: str, video_id: str, chunk_index: int) -> str:
        """Build hierarchical point ID as UUID"""
        import uuid
        import hashlib

        # Create a deterministic UUID from the hierarchical components
        hierarchical_string = f"{channel_id}:{video_id}:{chunk_index:04d}"

        # Generate a deterministic UUID using hash
        hash_bytes = hashlib.md5(hierarchical_string.encode()).digest()

        # Create UUID from hash
        point_uuid = str(uuid.UUID(bytes=hash_bytes))

        return point_uuid


def create_chunks_from_supadata_response(
    transcript_response: Dict[str, Any],
    channel_id: str,
    channel_name: str,
    video_id: str,
    video_title: str,
    video_url: str,
    publish_time: str,
    presenters: List[str] = None,
    category: str = "general",
    min_words: int = 120,
    max_words: int = 300,
) -> List[Dict[str, Any]]:
    """
    Complete pipeline: Supadata response → chunks → payloads

    Returns:
        List of (point_id, payload) tuples ready for Qdrant
    """

    # Initialize chunker
    chunker = TranscriptChunker(min_words=min_words, max_words=max_words)

    # Create chunks
    chunks = chunker.chunk_supadata_transcript(transcript_response)

    # Build payloads
    chunk_data = []
    for chunk in chunks:
        point_id = ChunkMetadataBuilder.build_hierarchical_id(
            channel_id, video_id, chunk.chunk_index
        )

        payload = ChunkMetadataBuilder.build_chunk_payload(
            chunk=chunk,
            channel_id=channel_id,
            channel_name=channel_name,
            video_id=video_id,
            video_title=video_title,
            video_url=video_url,
            publish_time=publish_time,
            presenters=presenters,
            category=category,
        )

        chunk_data.append(
            {"point_id": point_id, "payload": payload, "chunk_text": chunk.text}
        )

    logger.info(f"Created {len(chunk_data)} chunk payloads for video {video_id}")
    return chunk_data
