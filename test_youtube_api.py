#!/usr/bin/env python3
"""
Quick test of YouTube Data API v3 with the provided key
"""

import os
import sys
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Missing google-api-python-client. Install with:")
    print("   pip install google-api-python-client")
    sys.exit(1)

import asyncio
import aiohttp
import re

# API Key
YOUTUBE_API_KEY = "AIzaSyDARqb_bv3lgd2XadzaeBYKp4P4kJhpwtc"
CHANNEL_HANDLE = "@amitinvesting"


def test_youtube_api_key():
    """Test if YouTube API key works"""
    
    print("🔑 Testing YouTube API Key...")
    print("=" * 40)
    
    try:
        # Initialize YouTube API client
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # Test with a simple API call
        print("📡 Testing API connection...")
        response = youtube.search().list(
            part='snippet',
            q='test',
            maxResults=1
        ).execute()
        
        if response.get('items'):
            print("✅ YouTube API key is working!")
            print(f"   Quota cost: ~100 units")
            return youtube
        else:
            print("❌ API key works but returned no results")
            return None
            
    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        if "API_KEY_INVALID" in str(e):
            print("   → Check if API key is correct")
        elif "API_NOT_ACTIVATED" in str(e):
            print("   → Enable YouTube Data API v3 in Google Cloud Console")
        elif "QUOTA_EXCEEDED" in str(e):
            print("   → API quota exceeded for today")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def resolve_handle_with_api(youtube, handle):
    """Try to resolve handle using YouTube Data API"""
    
    print(f"\n🎯 Resolving handle: {handle}")
    print("-" * 30)
    
    clean_handle = handle.replace('@', '')
    
    # Method 1: Try forHandle parameter (not available in API v3)
    print("1️⃣ forHandle method not available in YouTube Data API v3")
    print("   ⚠️  Skipping this method")
    
    # Method 2: Try search
    try:
        print("2️⃣ Trying search method...")
        response = youtube.search().list(
            part='snippet',
            q=clean_handle,
            type='channel',
            maxResults=5
        ).execute()
        
        if response.get('items'):
            for item in response['items']:
                channel_id = item['snippet']['channelId']
                title = item['snippet']['title']
                custom_url = item['snippet'].get('customUrl', '')
                
                print(f"   📺 Found: {title}")
                print(f"   🆔 ID: {channel_id}")
                print(f"   🔗 Custom URL: {custom_url}")
                
                # Check if this matches our target
                if (clean_handle.lower() in title.lower() or 
                    clean_handle.lower() in custom_url.lower() or
                    'amit' in title.lower()):
                    print(f"   ✅ Potential match!")
                    return channel_id
        else:
            print(f"   ❌ No search results")
    except HttpError as e:
        print(f"   ❌ Search failed: {e}")
    
    return None


async def resolve_handle_with_web_scraping(handle):
    """Try to resolve handle by scraping YouTube page"""
    
    print("3️⃣ Trying web scraping method...")
    
    url = f"https://www.youtube.com/{handle}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Look for channel ID patterns
                    patterns = [
                        r'"channelId":"(UC[a-zA-Z0-9_-]{22})"',
                        r'"externalId":"(UC[a-zA-Z0-9_-]{22})"',
                        r'channel/(UC[a-zA-Z0-9_-]{22})',
                    ]
                    
                    for i, pattern in enumerate(patterns, 1):
                        match = re.search(pattern, html)
                        if match:
                            channel_id = match.group(1)
                            if channel_id.startswith('channel/'):
                                channel_id = channel_id.replace('channel/', '')
                            
                            print(f"   ✅ Found with pattern {i}: {channel_id}")
                            return channel_id
                    
                    print(f"   ❌ No channel ID found in HTML")
                else:
                    print(f"   ❌ HTTP {response.status}")
                    
    except Exception as e:
        print(f"   ❌ Web scraping error: {e}")
    
    return None


def test_channel_id(youtube, channel_id):
    """Test if channel ID works and get channel info"""
    
    print(f"\n📊 Testing channel ID: {channel_id}")
    print("-" * 40)
    
    try:
        response = youtube.channels().list(
            part='snippet,statistics',
            id=channel_id
        ).execute()
        
        if response.get('items'):
            item = response['items'][0]
            snippet = item['snippet']
            stats = item['statistics']
            
            print(f"✅ Channel verified!")
            print(f"📺 Title: {snippet['title']}")
            print(f"📝 Description: {snippet['description'][:100]}...")
            print(f"👥 Subscribers: {stats.get('subscriberCount', 'Hidden')}")
            print(f"📹 Videos: {stats.get('videoCount', 'Unknown')}")
            print(f"👀 Views: {stats.get('viewCount', 'Unknown')}")
            print(f"📅 Created: {snippet['publishedAt']}")
            
            return True
        else:
            print(f"❌ Channel ID not found")
            return False
            
    except HttpError as e:
        print(f"❌ Error verifying channel: {e}")
        return False


async def main():
    """Main test function"""
    
    print("🚀 YouTube API Test for @amitinvesting")
    print("=" * 50)
    
    # Test API key
    youtube = test_youtube_api_key()
    if not youtube:
        print("\n❌ Cannot proceed without working YouTube API")
        return
    
    # Try to resolve handle
    channel_id = resolve_handle_with_api(youtube, CHANNEL_HANDLE)
    
    if not channel_id:
        print("\n🔄 API methods failed, trying web scraping...")
        channel_id = await resolve_handle_with_web_scraping(CHANNEL_HANDLE)
    
    if channel_id:
        # Test the found channel ID
        test_channel_id(youtube, channel_id)
        
        print(f"\n🎯 Final Result:")
        print(f"Handle: {CHANNEL_HANDLE}")
        print(f"Channel ID: {channel_id}")
        print(f"Channel URL: https://www.youtube.com/channel/{channel_id}")
        
    else:
        print(f"\n❌ Could not resolve {CHANNEL_HANDLE} to channel ID")
        print("Trying known channel ID from previous research...")
        
        # Test known channel ID
        known_id = "UCjZnbgPb08NFg7MHyPQRZ3Q"
        if test_channel_id(youtube, known_id):
            print(f"\n✅ Known channel ID works: {known_id}")


if __name__ == "__main__":
    asyncio.run(main())