#!/usr/bin/env python3
"""
Debug script to test YouTube channel ID resolution
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Set up environment
from dotenv import load_dotenv
load_dotenv()

from services.youtube_service.app.utils.channel_resolver import YouTubeChannelResolver


async def test_channel_resolution():
    """Test channel ID resolution with detailed debugging"""
    
    print("🔍 YouTube Channel ID Resolution Debug")
    print("=" * 50)
    
    # Check API key
    youtube_api_key = os.getenv('YOUTUBE_API_KEY')
    print(f"📋 YouTube API Key: {'✅ Set' if youtube_api_key else '❌ Missing'}")
    
    if youtube_api_key:
        print(f"   Key length: {len(youtube_api_key)} characters")
        print(f"   Key preview: {youtube_api_key[:10]}...")
    
    print()
    
    # Test handles
    test_handles = [
        "@amitinvesting",
        "amitinvesting",
        "@mkbhd",  # Popular tech channel for comparison
        "mkbhd"
    ]
    
    resolver = YouTubeChannelResolver()
    
    for handle in test_handles:
        print(f"🎯 Testing handle: {handle}")
        print("-" * 30)
        
        try:
            channel_id = await resolver.resolve_handle_to_channel_id(handle)
            
            if channel_id:
                print(f"✅ Success: {channel_id}")
                
                # Validate format
                if resolver.validate_channel_id(channel_id):
                    print(f"✅ Valid format")
                else:
                    print(f"❌ Invalid format")
                
                # Test channel URL
                print(f"🔗 Channel URL: https://www.youtube.com/channel/{channel_id}")
                
            else:
                print(f"❌ Failed to resolve")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    # Test known channel ID
    print("🧪 Testing known channel ID...")
    known_channel_id = "UCjZnbgPb08NFg7MHyPQRZ3Q"  # From previous research
    
    if resolver.validate_channel_id(known_channel_id):
        print(f"✅ Known ID is valid: {known_channel_id}")
        
        # Test if we can use this ID with the API
        if resolver.youtube:
            try:
                response = resolver.youtube.channels().list(
                    part='snippet,statistics',
                    id=known_channel_id
                ).execute()
                
                if response.get('items'):
                    item = response['items'][0]
                    print(f"✅ Channel verified via API:")
                    print(f"   📺 Title: {item['snippet']['title']}")
                    print(f"   📝 Description: {item['snippet']['description'][:100]}...")
                    print(f"   👥 Subscribers: {item['statistics'].get('subscriberCount', 'Hidden')}")
                    print(f"   📹 Videos: {item['statistics'].get('videoCount', 'Unknown')}")
                else:
                    print(f"❌ Channel ID not found in API")
                    
            except Exception as e:
                print(f"❌ API test failed: {e}")
        else:
            print(f"⚠️  No YouTube API client available")
    else:
        print(f"❌ Known ID is invalid")


if __name__ == "__main__":
    asyncio.run(test_channel_resolution())