"""
Vector database integration using ChromaDB
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from parent directory
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from models import VectorDocument, ProcessedVideo
from retry_utils import gemini_api_retry

logger = logging.getLogger(__name__)


class ChromaVectorDB:
    """ChromaDB vector database manager"""

    def __init__(self):
        # Initialize ChromaDB client - prioritize Docker internal network, fallback to external/local
        chroma_host = os.getenv("CHROMA_DB_HOST", os.getenv("CHROMA_HOST", "localhost"))
        chroma_port = int(os.getenv("CHROMA_DB_PORT", os.getenv("CHROMA_PORT", 4545)))

        try:
            # Try connecting to Docker container first (single-tenant mode)
            self.client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
                settings=Settings(anonymized_telemetry=False),
            )
            # Test connection with basic list operation using v2 API
            try:
                collections = self.client.list_collections()
                logger.info(
                    f"✅ Connected to ChromaDB container at {chroma_host}:{chroma_port} (v2 API)"
                )
                logger.info(f"   📂 Found {len(collections)} existing collections")
                self.connection_type = "docker"
            except Exception as test_error:
                raise Exception(f"Container reachable but v2 API failed: {test_error}")

        except Exception as e:
            logger.warning(f"❌ Failed to connect to ChromaDB container: {e}")
            logger.info("🔄 Falling back to local persistent ChromaDB")
            try:
                # Fallback to local persistent client
                self.client = chromadb.PersistentClient(
                    path=os.getenv("CHROMA_DB_PATH", "./data/chroma_db"),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )
                logger.info("✅ Connected to local persistent ChromaDB")
                self.connection_type = "local"
            except Exception as local_error:
                logger.error(f"❌ Local ChromaDB also failed: {local_error}")
                logger.error(
                    "💡 Try installing chromadb with: uv add chromadb --upgrade"
                )
                raise Exception(
                    f"Both Docker and local ChromaDB failed. Docker: {e}, Local: {local_error}"
                )

        # Get or create collection for YouTube summaries
        self.collection = self.client.get_or_create_collection(
            name="youtube_summaries",
            metadata={"description": "YouTube video summaries and embeddings"},
        )

        # Initialize Gemini for embeddings
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        doc_count = self.collection.count()
        logger.info(
            f"🎯 ChromaDB ready: {doc_count} existing documents ({self.connection_type} connection)"
        )

    @gemini_api_retry
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini with exponential backoff retry"""
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
            title="YouTube Video Summary",
        )
        return result["embedding"]

    def document_exists(self, video_id: str) -> bool:
        """Check if a document already exists"""
        try:
            results = self.collection.get(where={"video_id": video_id})
            return len(results["ids"]) > 0
        except Exception as e:
            logger.error(f"Error checking document existence: {e}")
            return False

    def get_cached_transcript(self, video_id: str) -> Optional[str]:
        """Get cached transcript for a video ID"""
        try:
            results = self.collection.get(
                where={"video_id": video_id}, include=["metadatas"]
            )

            if results["ids"] and results["metadatas"]:
                transcript = results["metadatas"][0].get("transcript")
                if transcript:
                    logger.info(
                        f"Found cached transcript for {video_id} ({len(transcript)} characters)"
                    )
                    return transcript

            return None
        except Exception as e:
            logger.error(f"Error getting cached transcript for {video_id}: {e}")
            return None

    def cache_transcript(
        self, video_id: str, transcript: str, metadata: Dict[str, Any] = None
    ) -> bool:
        """Cache a transcript for future use"""
        try:
            # Check if transcript cache already exists
            existing = self.get_cached_transcript(video_id)
            if existing:
                logger.info(f"Transcript already cached for {video_id}")
                return True

            # Create a transcript-only document
            transcript_metadata = {
                "video_id": video_id,
                "transcript": transcript,
                "transcript_length": len(transcript),
                "cached_at": datetime.utcnow().isoformat(),
                "type": "transcript_cache",
            }

            # Add any additional metadata
            if metadata:
                transcript_metadata.update(metadata)

            # Generate embedding for transcript (for potential search)
            embedding = self.generate_embedding(
                transcript[:1000]
            )  # Use first 1000 chars for embedding

            # Add to ChromaDB with special ID for transcript cache
            cache_id = f"transcript_{video_id}"
            self.collection.add(
                ids=[cache_id],
                embeddings=[embedding],
                documents=[transcript],
                metadatas=[transcript_metadata],
            )

            logger.info(
                f"Cached transcript for {video_id} ({len(transcript)} characters)"
            )
            return True

        except Exception as e:
            logger.error(f"Error caching transcript for {video_id}: {e}")
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
            metadata = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "channel_url": channel_url,
                "recent_video_ids": ",".join(
                    recent_video_ids[:5]
                ),  # Store only 5 most recent
                "last_updated": datetime.utcnow().isoformat(),
                "type": "channel_metadata",
                "video_count": len(recent_video_ids),
            }

            # Use channel ID as the document ID
            cache_id = f"channel_{channel_id}"

            # Check if channel metadata already exists
            existing = self.collection.get(
                where={
                    "$and": [{"channel_id": channel_id}, {"type": "channel_metadata"}]
                }
            )

            if existing["ids"]:
                # Update existing record
                self.collection.update(ids=[cache_id], metadatas=[metadata])
                logger.info(
                    f"Updated channel metadata for {channel_name} with {len(recent_video_ids)} recent videos"
                )
            else:
                # Create new record
                embedding = self.generate_embedding(f"Channel: {channel_name}")
                self.collection.add(
                    ids=[cache_id],
                    embeddings=[embedding],
                    documents=[f"Channel: {channel_name} - Recent videos tracked"],
                    metadatas=[metadata],
                )
                logger.info(
                    f"Stored new channel metadata for {channel_name} with {len(recent_video_ids)} recent videos"
                )

            return True

        except Exception as e:
            logger.error(f"Error storing channel metadata for {channel_id}: {e}")
            return False

    def get_stored_video_ids(self, channel_id: str) -> List[str]:
        """Get previously stored video IDs for a channel"""
        try:
            results = self.collection.get(
                where={
                    "$and": [{"channel_id": channel_id}, {"type": "channel_metadata"}]
                },
                include=["metadatas"],
            )

            if results["metadatas"]:
                video_ids_str = results["metadatas"][0].get("recent_video_ids", "")
                if video_ids_str:
                    return video_ids_str.split(",")

            return []
        except Exception as e:
            logger.error(f"Error getting stored video IDs for {channel_id}: {e}")
            return []

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

            # Prepare metadata
            metadata = {
                "video_id": processed_video.video_id,
                "channel_name": processed_video.metadata.channel_name,
                "channel_url": processed_video.metadata.channel_url,
                "presenters": ",".join(processed_video.metadata.presenters),
                "title": processed_video.metadata.title,
                "publish_time": processed_video.metadata.publish_time,
                "video_url": processed_video.metadata.video_url,
                "category": processed_video.metadata.category,
                "transcript_length": processed_video.transcript_length,
                "last_processed": processed_video.last_processed,
                "duration": processed_video.metadata.duration or "",
                "view_count": processed_video.metadata.view_count or 0,
            }

            # Add to ChromaDB
            self.collection.add(
                ids=[processed_video.video_id],
                embeddings=[embedding],
                documents=[processed_video.summary],
                metadatas=[metadata],
            )

            logger.info(f"Added video {processed_video.video_id} to vector database")
            return True

        except Exception as e:
            logger.error(f"Error adding document to vector database: {e}")
            return False

    def add_documents_batch(self, processed_videos: List[ProcessedVideo]) -> int:
        """Add multiple documents in batch"""
        added_count = 0

        for video in processed_videos:
            if self.add_document(video):
                added_count += 1

        logger.info(f"Added {added_count} new documents to vector database")
        return added_count

    def search_similar(
        self,
        query: str,
        n_results: int = 10,
        channel_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents with retry logic for embedding generation"""
        try:
            # Generate query embedding (already has retry logic)
            query_embedding = self.generate_embedding(query)

            # Build where clause for filtering
            where_clause = {}
            if channel_filter:
                where_clause["channel_name"] = channel_filter
            if category_filter:
                where_clause["category"] = category_filter

            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"],
            )

            # Format results
            formatted_results = []
            for i in range(len(results["ids"][0])):
                result = {
                    "video_id": results["ids"][0][i],
                    "summary": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity_score": 1
                    - results["distances"][0][i],  # Convert distance to similarity
                }

                # Parse presenters back to list
                if result["metadata"].get("presenters"):
                    result["metadata"]["presenters"] = result["metadata"][
                        "presenters"
                    ].split(",")

                formatted_results.append(result)

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return []

    def get_recent_videos(
        self, n_results: int = 20, channel_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get most recently processed videos"""
        try:
            where_clause = {}
            if channel_filter:
                where_clause["channel_name"] = channel_filter

            # Get all documents and sort by last_processed
            results = self.collection.get(
                where=where_clause if where_clause else None,
                include=["documents", "metadatas"],
            )

            # Sort by last_processed timestamp
            video_data = []
            for i in range(len(results["ids"])):
                video_data.append(
                    {
                        "video_id": results["ids"][i],
                        "summary": results["documents"][i],
                        "metadata": results["metadatas"][i],
                        "last_processed": results["metadatas"][i].get(
                            "last_processed", ""
                        ),
                    }
                )

            # Sort by last_processed (most recent first)
            video_data.sort(key=lambda x: x["last_processed"], reverse=True)

            # Return top n_results
            return video_data[:n_results]

        except Exception as e:
            logger.error(f"Error getting recent videos: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            total_docs = self.collection.count()

            # Get channel distribution
            all_docs = self.collection.get(include=["metadatas"])
            channel_counts = {}
            category_counts = {}

            for metadata in all_docs["metadatas"]:
                channel = metadata.get("channel_name", "Unknown")
                category = metadata.get("category", "Unknown")

                channel_counts[channel] = channel_counts.get(channel, 0) + 1
                category_counts[category] = category_counts.get(category, 0) + 1

            return {
                "total_documents": total_docs,
                "channel_distribution": channel_counts,
                "category_distribution": category_counts,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    def delete_document(self, video_id: str) -> bool:
        """Delete a document by video ID"""
        try:
            self.collection.delete(where={"video_id": video_id})
            logger.info(f"Deleted video {video_id} from vector database")
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False

    def reset_database(self) -> bool:
        """Reset the entire database (use with caution)"""
        try:
            self.client.delete_collection("youtube_summaries")
            self.collection = self.client.create_collection(
                name="youtube_summaries",
                metadata={"description": "YouTube video summaries and embeddings"},
            )
            logger.warning("Vector database has been reset")
            return True
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False
