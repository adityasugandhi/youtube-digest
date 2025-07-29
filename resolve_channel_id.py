#!/usr/bin/env python3
"""
Script to resolve YouTube handle to channel ID
Usage:
  python resolve_channel_id.py @amitinvesting
  python resolve_channel_id.py --api-key YOUR_API_KEY @amitinvesting

Requirements:
  pip install google-api-python-client

Setup:
  1. Get a YouTube Data API v3 key from Google Cloud Console
  2. Either set YOUTUBE_API_KEY environment variable or use --api-key flag
"""

import asyncio
import sys
import os
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class SimpleYouTubeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    async def resolve_handle_to_channel_id(self, handle: str):
        """Resolve a YouTube handle (@username) to a channel ID"""

        try:
            # Remove @ if present
            clean_handle = handle.lstrip('@')
            print(f"Trying to resolve: {clean_handle}")

            # Method 1: Use forUsername parameter (works for legacy usernames)
            try:
                response = await asyncio.to_thread(
                    self.youtube.channels().list,
                    part='id,snippet',
                    forUsername=clean_handle
                )

                if response['items']:
                    channel_id = response['items'][0]['id']
                    print(f"✅ Found via forUsername: {channel_id}")
                    return {
                        'channel_id': channel_id,
                        'method': 'forUsername',
                        'title': response['items'][0]['snippet']['title']
                    }
            except Exception as e:
                print(f"forUsername method failed: {e}")

            # Method 2: Search API with @handle
            try:
                search_response = await asyncio.to_thread(
                    self.youtube.search().list,
                    part='snippet',
                    q=f"@{clean_handle}",
                    type='channel',
                    maxResults=5
                )

                if search_response['items']:
                    # Look for exact match
                    for item in search_response['items']:
                        custom_url = item['snippet'].get('customUrl', '')
                        custom_url = custom_url.lower()
                        if custom_url == f"@{clean_handle.lower()}":
                            channel_id = item['snippet']['channelId']
                            msg = "✅ Found via search (exact match)"
                            print(f"{msg}: {channel_id}")
                            return {
                                'channel_id': channel_id,
                                'method': 'search_exact',
                                'title': item['snippet']['title'],
                                'custom_url': custom_url
                            }

                    # If no exact match, return the first result
                    item = search_response['items'][0]
                    channel_id = item['snippet']['channelId']
                    print(f"⚠️  Found via search (first result): {channel_id}")
                    return {
                        'channel_id': channel_id,
                        'method': 'search_first',
                        'title': item['snippet']['title'],
                        'custom_url': item['snippet'].get('customUrl', '')
                    }
            except Exception as e:
                print(f"Search method failed: {e}")

            # Method 3: Try without @ prefix
            try:
                search_response = await asyncio.to_thread(
                    self.youtube.search().list,
                    part='snippet',
                    q=clean_handle,
                    type='channel',
                    maxResults=5
                )

                if search_response['items']:
                    for item in search_response['items']:
                        custom_url = item['snippet'].get('customUrl', '')
                        custom_url = custom_url.lower()
                        title_lower = item['snippet']['title'].lower()
                        if (custom_url == f"@{clean_handle.lower()}" or
                                clean_handle.lower() in title_lower):
                            channel_id = item['snippet']['channelId']
                            print(f"✅ Found via search (no @): {channel_id}")
                            return {
                                'channel_id': channel_id,
                                'method': 'search_no_at',
                                'title': item['snippet']['title'],
                                'custom_url': custom_url
                            }
            except Exception as e:
                print(f"Search without @ method failed: {e}")

            return None

        except HttpError as e:
            print(f"YouTube API error resolving handle {handle}: {e}")
            return None
        except Exception as e:
            print(f"Error resolving handle {handle}: {e}")
            return None


async def resolve_handle(handle: str, api_key: str):
    """Resolve a YouTube handle to channel ID"""
    client = SimpleYouTubeClient(api_key)

    print(f"Resolving handle: {handle}")
    print("-" * 50)

    result = await client.resolve_handle_to_channel_id(handle)

    if result:
        print("-" * 50)
        print("🎉 SUCCESS!")
        print(f"Channel ID: {result['channel_id']}")
        print(f"Channel Title: {result['title']}")
        print(f"Method Used: {result['method']}")
        if 'custom_url' in result and result['custom_url']:
            print(f"Custom URL: {result['custom_url']}")
        channel_url = f"https://www.youtube.com/channel/{result['channel_id']}"
        print(f"Channel URL: {channel_url}")
        handle_url = f"https://www.youtube.com/@{handle.lstrip('@')}"
        print(f"Handle URL: {handle_url}")
        print("-" * 50)

        # Also create a summary for easy copy-paste
        print("\n📋 Summary for API usage:")
        print(f"Channel ID: {result['channel_id']}")

        return result['channel_id']
    else:
        print("-" * 50)
        print("❌ Could not resolve channel ID")
        print("Try the following:")
        print("1. Check if the handle is correct")
        print("2. Verify the channel exists and is public")
        print("3. Try searching manually on YouTube")
        print("-" * 50)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Resolve YouTube handle to channel ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python resolve_channel_id.py @amitinvesting
  python resolve_channel_id.py --api-key YOUR_KEY @amitinvesting

Environment Setup:
  export YOUTUBE_API_KEY=your_youtube_api_key_here
        """
    )

    parser.add_argument('handle',
                        help='YouTube handle (e.g., @amitinvesting)')
    parser.add_argument('--api-key',
                        help='YouTube Data API v3 key '
                        '(overrides YOUTUBE_API_KEY env var)')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ Error: YouTube API key not provided")
        print("\nOption 1: Set environment variable")
        print("  export YOUTUBE_API_KEY=your_youtube_api_key_here")
        print("\nOption 2: Use --api-key flag")
        print("  python resolve_channel_id.py --api-key YOUR_KEY @amitinvesting")
        url = "https://console.cloud.google.com/apis/credentials"
        print(f"\nGet API key from: {url}")
        sys.exit(1)

    try:
        asyncio.run(resolve_handle(args.handle, api_key))
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()