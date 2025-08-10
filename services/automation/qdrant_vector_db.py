"""
Qdrant vector database integration for YouTube transcripts
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    CreateCollection,
)
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from models import ProcessedVideo
from chunking_utils import create_chunks_from_supadata_response

logger = logging.getLogger(__name__)


class QdrantVectorDB:
    """Qdrant vector database manager with e5-base-v2 embeddings"""

    def __init__(self):
        # Initialize Qdrant client
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = os.getenv("COLLECTION_YT", "youtube_transcripts")
        self.embed_model_name = os.getenv("EMBED_MODEL", "intfloat/e5-base-v2")

        try:
            self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)

            # Test connection
            collections = self.client.get_collections()
            logger.info(
                f"✅ Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}"
            )
            logger.info(f"📂 Found {len(collections.collections)} existing collections")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise Exception(f"Qdrant connection failed: {e}")

        # Initialize embedding model
        try:
            self.embed_model = SentenceTransformer(self.embed_model_name)
            logger.info(f"✅ Loaded embedding model: {self.embed_model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise Exception(f"Embedding model loading failed: {e}")

        # Ensure collection exists
        self._ensure_collection()

        # Get document count
        try:
            collection_info = self.client.get_collection(self.collection_name)
            doc_count = collection_info.points_count
            logger.info(f"🎯 Qdrant ready: {doc_count} existing documents")
        except Exception as e:
            logger.warning(f"Could not get collection info: {e}")

    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration"""
        try:
            # Try to get existing collection
            self.client.get_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception:
            # Create new collection
            try:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # e5-base-v2 embedding dimension
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"✅ Created collection '{self.collection_name}'")
            except Exception as e:
                logger.error(f"Failed to create collection: {e}")
                raise

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using e5-base-v2"""
        try:
            # Add passage prefix for e5 models
            prefixed_text = f"passage: {text}"
            embedding = self.embed_model.encode(
                prefixed_text, normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            prefixed_texts = [f"passage: {text}" for text in texts]
            embeddings = self.embed_model.encode(
                prefixed_texts, normalize_embeddings=True
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    def document_exists(self, video_id: str) -> bool:
        """Check if a document already exists"""
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="video_id", match=MatchValue(value=video_id))
                    ]
                ),
                limit=1,
            )
            return len(results[0]) > 0
        except Exception as e:
            logger.error(f"Error checking document existence: {e}")
            return False

    def add_document(self, processed_video: ProcessedVideo) -> bool:
        """Add a processed video to the vector database"""
        try:
            # Check if already exists
            if self.document_exists(processed_video.video_id):
                logger.info(
                    f"Video {processed_video.video_id} already exists, skipping"
                )
                return False

            # Generate embedding
            embedding = self.generate_embedding(processed_video.summary)

            # Create payload
            payload = {
                "video_id": processed_video.video_id,
                "channel_name": processed_video.metadata.channel_name,
                "channel_url": processed_video.metadata.channel_url,
                "presenters": processed_video.metadata.presenters,
                "title": processed_video.metadata.title,
                "publish_time": processed_video.metadata.publish_time,
                "video_url": processed_video.metadata.video_url,
                "category": processed_video.metadata.category,
                "transcript_length": processed_video.transcript_length,
                "last_processed": processed_video.last_processed,
                "duration": processed_video.metadata.duration or "",
                "view_count": processed_video.metadata.view_count or 0,
                "summary": processed_video.summary,
                "type": "video_summary",
            }

            # Create point
            point = PointStruct(
                id=processed_video.video_id, vector=embedding, payload=payload
            )

            # Upsert to Qdrant
            self.client.upsert(collection_name=self.collection_name, points=[point])

            logger.info(f"Added video {processed_video.video_id} to Qdrant")
            return True

        except Exception as e:
            logger.error(f"Error adding document to Qdrant: {e}")
            return False

    def add_documents_batch(self, processed_videos: List[ProcessedVideo]) -> int:
        """Add multiple documents in batch"""
        try:
            points = []
            added_count = 0

            for video in processed_videos:
                if not self.document_exists(video.video_id):
                    embedding = self.generate_embedding(video.summary)

                    payload = {
                        "video_id": video.video_id,
                        "channel_name": video.metadata.channel_name,
                        "channel_url": video.metadata.channel_url,
                        "presenters": video.metadata.presenters,
                        "title": video.metadata.title,
                        "publish_time": video.metadata.publish_time,
                        "video_url": video.metadata.video_url,
                        "category": video.metadata.category,
                        "transcript_length": video.transcript_length,
                        "last_processed": video.last_processed,
                        "duration": video.metadata.duration or "",
                        "view_count": video.metadata.view_count or 0,
                        "summary": video.summary,
                        "type": "video_summary",
                    }

                    points.append(
                        PointStruct(
                            id=video.video_id, vector=embedding, payload=payload
                        )
                    )
                    added_count += 1

            if points:
                self.client.upsert(collection_name=self.collection_name, points=points)

            logger.info(f"Added {added_count} new documents to Qdrant")
            return added_count

        except Exception as e:
            logger.error(f"Error adding batch documents: {e}")
            return 0

    def search_similar(
        self,
        query: str,
        n_results: int = 10,
        channel_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Generate query embedding (with query prefix for e5)
            query_embedding = self.embed_model.encode(
                f"query: {query}", normalize_embeddings=True
            ).tolist()

            # Build filter
            must_conditions = [
                FieldCondition(key="type", match=MatchValue(value="video_summary"))
            ]

            if channel_filter:
                must_conditions.append(
                    FieldCondition(
                        key="channel_name", match=MatchValue(value=channel_filter)
                    )
                )
            if category_filter:
                must_conditions.append(
                    FieldCondition(
                        key="category", match=MatchValue(value=category_filter)
                    )
                )

            search_filter = (
                Filter(must=must_conditions) if len(must_conditions) > 1 else None
            )

            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=n_results,
                with_payload=True,
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_result = {
                    "video_id": result.payload["video_id"],
                    "summary": result.payload["summary"],
                    "metadata": {
                        k: v for k, v in result.payload.items() if k != "summary"
                    },
                    "similarity_score": result.score,
                }
                formatted_results.append(formatted_result)

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            return []

    def get_recent_videos(
        self, n_results: int = 20, channel_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get most recently processed videos"""
        try:
            must_conditions = [
                FieldCondition(key="type", match=MatchValue(value="video_summary"))
            ]

            if channel_filter:
                must_conditions.append(
                    FieldCondition(
                        key="channel_name", match=MatchValue(value=channel_filter)
                    )
                )

            search_filter = Filter(must=must_conditions)

            # Scroll through all documents
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                with_payload=True,
                limit=10000,  # Get all, we'll sort and limit later
            )

            # Sort by last_processed
            video_data = []
            for point in results:
                video_data.append(
                    {
                        "video_id": point.payload["video_id"],
                        "summary": point.payload["summary"],
                        "metadata": {
                            k: v for k, v in point.payload.items() if k != "summary"
                        },
                        "last_processed": point.payload.get("last_processed", ""),
                    }
                )

            # Sort by last_processed (most recent first)
            video_data.sort(key=lambda x: x["last_processed"], reverse=True)

            return video_data[:n_results]

        except Exception as e:
            logger.error(f"Error getting recent videos: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            collection_info = self.client.get_collection(self.collection_name)

            # Get all documents to count by channel/category
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type", match=MatchValue(value="video_summary")
                        )
                    ]
                ),
                with_payload=True,
                limit=10000,
            )

            channel_counts = {}
            category_counts = {}

            for point in results:
                channel = point.payload.get("channel_name", "Unknown")
                category = point.payload.get("category", "Unknown")

                channel_counts[channel] = channel_counts.get(channel, 0) + 1
                category_counts[category] = category_counts.get(category, 0) + 1

            return {
                "total_documents": len(results),
                "total_points": collection_info.points_count,
                "channel_distribution": channel_counts,
                "category_distribution": category_counts,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def delete_document(self, video_id: str) -> bool:
        """Delete a document by video ID"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="video_id", match=MatchValue(value=video_id))
                    ]
                ),
            )
            logger.info(f"Deleted video {video_id} from Qdrant")
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False

    def reset_database(self) -> bool:
        """Reset the entire database (use with caution)"""
        try:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()
            logger.warning("Qdrant database has been reset")
            return True
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False

    def store_channel_metadata(
        self,
        channel_id: str,
        channel_name: str,
        channel_url: str,
        recent_video_ids: List[str],
    ) -> bool:
        """Store channel metadata and recent video IDs"""
        try:
            payload = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "channel_url": channel_url,
                "recent_video_ids": recent_video_ids[:5],  # Store only 5 most recent
                "last_updated": datetime.utcnow().isoformat(),
                "type": "channel_metadata",
                "video_count": len(recent_video_ids),
            }

            # Generate embedding
            embedding = self.generate_embedding(f"Channel: {channel_name}")

            # Create point with UUID
            from chunking_utils import ChunkMetadataBuilder

            point_uuid = ChunkMetadataBuilder.build_hierarchical_id(
                f"channel_{channel_id}", "metadata", 0
            )
            point = PointStruct(id=point_uuid, vector=embedding, payload=payload)

            # Upsert to Qdrant
            self.client.upsert(collection_name=self.collection_name, points=[point])

            logger.info(
                f"Stored channel metadata for {channel_name} with {len(recent_video_ids)} recent videos"
            )
            return True

        except Exception as e:
            logger.error(f"Error storing channel metadata: {e}")
            return False

    def add_transcript_chunks(
        self,
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
    ) -> int:
        """
        Add transcript chunks with hierarchical structure

        Returns:
            Number of chunks successfully added
        """
        try:
            # Check if chunks already exist for this video
            if self.video_chunks_exist(video_id):
                logger.info(f"Skipping {video_id} - chunks already exist")
                return 0
            # Create chunks from Supadata response
            chunk_data = create_chunks_from_supadata_response(
                transcript_response=transcript_response,
                channel_id=channel_id,
                channel_name=channel_name,
                video_id=video_id,
                video_title=video_title,
                video_url=video_url,
                publish_time=publish_time,
                presenters=presenters,
                category=category,
                min_words=min_words,
                max_words=max_words,
            )

            if not chunk_data:
                logger.warning(f"No chunks created for video {video_id}")
                return 0

            # Generate embeddings for all chunks
            chunk_texts = [chunk["chunk_text"] for chunk in chunk_data]
            embeddings = self.generate_embeddings_batch(chunk_texts)

            # Create points
            points = []
            for chunk, embedding in zip(chunk_data, embeddings):
                point = PointStruct(
                    id=chunk["point_id"], vector=embedding, payload=chunk["payload"]
                )
                points.append(point)

            # Batch upsert to Qdrant
            batch_size = 100
            added_count = 0

            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                try:
                    self.client.upsert(
                        collection_name=self.collection_name, points=batch
                    )
                    added_count += len(batch)
                except Exception as e:
                    logger.error(f"Error upserting batch {i//batch_size + 1}: {e}")
                    continue

            logger.info(f"Added {added_count} transcript chunks for video {video_id}")
            return added_count

        except Exception as e:
            logger.error(f"Error adding transcript chunks: {e}")
            return 0

    def video_chunks_exist(self, video_id: str) -> bool:
        """Check if transcript chunks already exist for a video"""
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="video_id", match=MatchValue(value=video_id))
                    ]
                ),
                limit=1,
                with_payload=False,
            )

            exists = len(results[0]) > 0
            if exists:
                logger.info(f"Video chunks already exist for {video_id}")
            return exists

        except Exception as e:
            logger.warning(f"Error checking video chunks existence for {video_id}: {e}")
            return False

    def search_chunks(
        self,
        query: str,
        channel_filter: Optional[str] = None,
        video_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Search transcript chunks with hierarchical filtering

        Args:
            query: Search query text
            channel_filter: Filter by channel_id or channel_name
            video_filter: Filter by specific video_id
            category_filter: Filter by category
            limit: Maximum results to return
            score_threshold: Minimum similarity score

        Returns:
            List of chunk results with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embed_model.encode(
                f"query: {query}", normalize_embeddings=True
            ).tolist()

            # Build filter conditions
            must_conditions = [
                FieldCondition(key="type", match=MatchValue(value="transcript_chunk"))
            ]

            if channel_filter:
                # Try both channel_id and channel_name
                must_conditions.append(
                    FieldCondition(
                        key="channel_id", match=MatchValue(value=channel_filter)
                    )
                )

            if video_filter:
                must_conditions.append(
                    FieldCondition(key="video_id", match=MatchValue(value=video_filter))
                )

            if category_filter:
                must_conditions.append(
                    FieldCondition(
                        key="category", match=MatchValue(value=category_filter)
                    )
                )

            search_filter = Filter(must=must_conditions) if must_conditions else None

            # Search chunks
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
                score_threshold=score_threshold,
            )

            # Format results
            formatted_results = []
            for result in results:
                chunk_result = {
                    "point_id": result.id,
                    "score": result.score,
                    "chunk_text": result.payload["chunk_text"],
                    "channel_name": result.payload["channel_name"],
                    "video_title": result.payload["video_title"],
                    "video_id": result.payload["video_id"],
                    "timestamped_url": result.payload["timestamped_url"],
                    "start_ms": result.payload["start_ms"],
                    "end_ms": result.payload["end_ms"],
                    "chunk_index": result.payload["chunk_index"],
                    "metadata": result.payload,
                }
                formatted_results.append(chunk_result)

            logger.info(
                f"Found {len(formatted_results)} chunks for query: '{query[:50]}...'"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching chunks: {e}")
            return []

    def get_video_chunks(
        self, video_id: str, channel_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a specific video"""
        try:
            must_conditions = [
                FieldCondition(key="type", match=MatchValue(value="transcript_chunk")),
                FieldCondition(key="video_id", match=MatchValue(value=video_id)),
            ]

            if channel_id:
                must_conditions.append(
                    FieldCondition(key="channel_id", match=MatchValue(value=channel_id))
                )

            search_filter = Filter(must=must_conditions)

            # Scroll through all chunks for this video
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                with_payload=True,
                limit=1000,  # Should be enough for most videos
            )

            # Sort by chunk_index
            chunks = []
            for point in results:
                chunk = {
                    "point_id": point.id,
                    "chunk_text": point.payload["chunk_text"],
                    "chunk_index": point.payload["chunk_index"],
                    "start_ms": point.payload["start_ms"],
                    "end_ms": point.payload["end_ms"],
                    "timestamped_url": point.payload["timestamped_url"],
                    "metadata": point.payload,
                }
                chunks.append(chunk)

            # Sort by chunk index
            chunks.sort(key=lambda x: x["chunk_index"])

            logger.info(f"Retrieved {len(chunks)} chunks for video {video_id}")
            return chunks

        except Exception as e:
            logger.error(f"Error getting video chunks: {e}")
            return []

    def get_channel_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get all videos for a channel (from chunk metadata)"""
        try:
            # Get all chunks for this channel
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="type", match=MatchValue(value="transcript_chunk")
                    ),
                    FieldCondition(
                        key="channel_id", match=MatchValue(value=channel_id)
                    ),
                ]
            )

            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                with_payload=True,
                limit=10000,
            )

            # Group by video_id
            videos = {}
            for point in results:
                video_id = point.payload["video_id"]
                if video_id not in videos:
                    videos[video_id] = {
                        "video_id": video_id,
                        "video_title": point.payload["video_title"],
                        "video_url": point.payload["video_url"],
                        "publish_time": point.payload["publish_time"],
                        "chunk_count": 0,
                        "total_duration_ms": 0,
                    }

                videos[video_id]["chunk_count"] += 1
                videos[video_id]["total_duration_ms"] = max(
                    videos[video_id]["total_duration_ms"], point.payload["end_ms"]
                )

            video_list = list(videos.values())
            video_list.sort(key=lambda x: x["publish_time"], reverse=True)

            logger.info(f"Found {len(video_list)} videos for channel {channel_id}")
            return video_list

        except Exception as e:
            logger.error(f"Error getting channel videos: {e}")
            return []

    def delete_video_chunks(
        self, video_id: str, channel_id: Optional[str] = None
    ) -> int:
        """Delete all chunks for a specific video"""
        try:
            must_conditions = [
                FieldCondition(key="type", match=MatchValue(value="transcript_chunk")),
                FieldCondition(key="video_id", match=MatchValue(value=video_id)),
            ]

            if channel_id:
                must_conditions.append(
                    FieldCondition(key="channel_id", match=MatchValue(value=channel_id))
                )

            delete_filter = Filter(must=must_conditions)

            # Get count before deletion
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=delete_filter,
                limit=1,
            )

            # Delete chunks
            self.client.delete(
                collection_name=self.collection_name, points_selector=delete_filter
            )

            logger.info(f"Deleted chunks for video {video_id}")
            return len(results)

        except Exception as e:
            logger.error(f"Error deleting video chunks: {e}")
            return 0
