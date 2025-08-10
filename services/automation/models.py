"""
Data models for the YouTube automation pipeline
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


@dataclass
class YouTubeChannel:
    """YouTube channel configuration"""

    channel_name: str
    channel_url: str
    presenters: List[str]
    channel_id: Optional[str] = None
    enabled: bool = True
    last_processed: Optional[str] = None
    category: str = "investing"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YouTubeChannel":
        return cls(**data)


@dataclass
class VideoMetadata:
    """Video metadata for processing"""

    video_id: str
    title: str
    channel_name: str
    channel_url: str
    presenters: List[str]
    publish_time: str
    video_url: str
    duration: Optional[str] = None
    view_count: Optional[int] = None
    category: str = "investing"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessedVideo:
    """Processed video with summary and embedding"""

    video_id: str
    metadata: VideoMetadata
    summary: str
    transcript_length: int
    processing_status: str = "completed"
    last_processed: str = datetime.utcnow().isoformat()
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["metadata"] = self.metadata.to_dict()
        return data


@dataclass
class VectorDocument:
    """Document structure for vector database"""

    page_content: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"page_content": self.page_content, "metadata": self.metadata}


class CreatorListManager:
    """Manages the YouTube creators list"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._channels = None

    def load_channels(self) -> List[YouTubeChannel]:
        """Load channels from JSON file"""
        if self._channels is None:
            with open(self.file_path, "r") as f:
                data = json.load(f)
            self._channels = [YouTubeChannel.from_dict(item) for item in data]
        return self._channels

    def save_channels(self, channels: List[YouTubeChannel]) -> None:
        """Save channels to JSON file"""
        data = [channel.to_dict() for channel in channels]
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)
        self._channels = channels

    def get_enabled_channels(self) -> List[YouTubeChannel]:
        """Get only enabled channels"""
        channels = self.load_channels()
        return [channel for channel in channels if channel.enabled]

    def update_last_processed(self, channel_name: str, timestamp: str) -> None:
        """Update last processed timestamp for a channel"""
        channels = self.load_channels()
        for channel in channels:
            if channel.channel_name == channel_name:
                channel.last_processed = timestamp
                break
        self.save_channels(channels)

    def add_channel(self, channel: YouTubeChannel) -> None:
        """Add a new channel"""
        channels = self.load_channels()
        channels.append(channel)
        self.save_channels(channels)

    def remove_channel(self, channel_name: str) -> None:
        """Remove a channel by name"""
        channels = self.load_channels()
        channels = [c for c in channels if c.channel_name != channel_name]
        self.save_channels(channels)

    def enable_channel(self, channel_name: str, enabled: bool = True) -> None:
        """Enable or disable a channel"""
        channels = self.load_channels()
        for channel in channels:
            if channel.channel_name == channel_name:
                channel.enabled = enabled
                break
        self.save_channels(channels)
