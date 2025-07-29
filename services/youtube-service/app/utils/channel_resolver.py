import re
import aiohttp
import logging
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings

logger = logging.getLogger(__name__)


class YouTubeChannelResolver:
    """Resolve YouTube handles to channel IDs using multiple methods"""
    
    def __init__(self):
        self.api_key = settings.youtube_api_key
        self.youtube = None
        if self.api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {e}")
    
    async def resolve_handle_to_channel_id(self, handle: str) -> Optional[str]:
        """
        Resolve YouTube handle to channel ID using multiple methods
        
        Args:
            handle: YouTube handle (e.g., "@amitinvesting" or "amitinvesting")
        
        Returns:
            Channel ID (e.g., "UCjZnbgPb08NFg7MHyPQRZ3Q") or None if not found
        """
        
        # Clean handle
        clean_handle = handle.replace('@', '').strip()
        
        # Method 1: Try YouTube Data API v3 with forHandle
        if self.youtube:
            channel_id = await self._resolve_with_api(clean_handle)
            if channel_id:
                return channel_id
        
        # Method 2: Try web scraping as fallback
        channel_id = await self._resolve_with_web_scraping(handle)
        if channel_id:
            return channel_id
        
        # Method 3: Try search API
        if self.youtube:
            channel_id = await self._resolve_with_search(clean_handle)
            if channel_id:
                return channel_id
        
        logger.warning(f"Could not resolve handle '{handle}' to channel ID")
        return None
    
    async def _resolve_with_api(self, handle: str) -> Optional[str]:
        """Try to resolve using YouTube Data API v3 forHandle parameter"""
        
        try:
            response = self.youtube.channels().list(
                part='id',
                forHandle=handle
            ).execute()
            
            if response.get('items'):
                channel_id = response['items'][0]['id']
                logger.info(f"Resolved handle '{handle}' to channel ID '{channel_id}' via API")
                return channel_id
                
        except HttpError as e:
            logger.debug(f"API method failed for handle '{handle}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error in API method: {e}")
        
        return None
    
    async def _resolve_with_web_scraping(self, handle: str) -> Optional[str]:
        """Try to resolve by scraping the YouTube page"""
        
        # Construct URL
        if handle.startswith('@'):
            url = f"https://www.youtube.com/{handle}"
        else:
            url = f"https://www.youtube.com/@{handle}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Look for channel ID in various places in the HTML
                        patterns = [
                            r'"channelId":"(UC[a-zA-Z0-9_-]{22})"',
                            r'"externalId":"(UC[a-zA-Z0-9_-]{22})"',
                            r'channel/(UC[a-zA-Z0-9_-]{22})',
                            r'"webCommandMetadata":\{"url":"/(channel/UC[a-zA-Z0-9_-]{22})"',
                            r'"canonicalBaseUrl":"/(channel/UC[a-zA-Z0-9_-]{22})"'
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, html)
                            if match:
                                channel_id = match.group(1)
                                if channel_id.startswith('channel/'):
                                    channel_id = channel_id.replace('channel/', '')
                                
                                logger.info(f"Resolved handle '{handle}' to channel ID '{channel_id}' via web scraping")
                                return channel_id
                        
                        # Look for redirect to channel URL
                        redirect_match = re.search(r'href="https://www\.youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})"', html)
                        if redirect_match:
                            channel_id = redirect_match.group(1)
                            logger.info(f"Resolved handle '{handle}' to channel ID '{channel_id}' via redirect")
                            return channel_id
                    
                    else:
                        logger.debug(f"HTTP {response.status} when accessing {url}")
                        
        except Exception as e:
            logger.debug(f"Web scraping failed for handle '{handle}': {e}")
        
        return None
    
    async def _resolve_with_search(self, handle: str) -> Optional[str]:
        """Try to resolve using YouTube search API"""
        
        try:
            # Search for the handle
            search_response = self.youtube.search().list(
                part='snippet',
                q=handle,
                type='channel',
                maxResults=5
            ).execute()
            
            # Look for exact or close matches
            for item in search_response.get('items', []):
                channel_title = item['snippet']['title'].lower()
                channel_handle = item['snippet'].get('customUrl', '').lower()
                
                # Check if this looks like our target channel
                if (handle.lower() in channel_title or 
                    handle.lower() in channel_handle or
                    channel_title in handle.lower()):
                    
                    channel_id = item['snippet']['channelId']
                    logger.info(f"Resolved handle '{handle}' to channel ID '{channel_id}' via search")
                    return channel_id
                    
        except HttpError as e:
            logger.debug(f"Search method failed for handle '{handle}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error in search method: {e}")
        
        return None
    
    def validate_channel_id(self, channel_id: str) -> bool:
        """Validate that a channel ID has the correct format"""
        
        if not channel_id:
            return False
        
        # YouTube channel IDs are 24 characters long and start with UC
        pattern = r'^UC[a-zA-Z0-9_-]{22}$'
        return bool(re.match(pattern, channel_id))


# Global resolver instance
channel_resolver = YouTubeChannelResolver()


async def resolve_youtube_handle(handle: str) -> Optional[str]:
    """
    Convenience function to resolve YouTube handle to channel ID
    
    Args:
        handle: YouTube handle (e.g., "@amitinvesting")
    
    Returns:
        Channel ID or None if not found
    """
    return await channel_resolver.resolve_handle_to_channel_id(handle)