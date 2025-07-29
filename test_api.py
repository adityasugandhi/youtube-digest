#!/usr/bin/env python3
"""
Test script for YouTube Digest Backend API
Tests the @amitinvesting channel for recent live streams
"""

import asyncio
import aiohttp
import json
import sys
import os
from typing import Dict, List

# Test configuration
YOUTUBE_SERVICE_URL = "http://localhost:8001"
DIGEST_SERVICE_URL = "http://localhost:8002"
CHANNEL_HANDLE = "@amitinvesting"
CHANNEL_ID = "UCjZnbgPb08NFg7MHyPQRZ3Q"
MAX_RESULTS = 5


async def test_youtube_service():
    """Test YouTube service endpoints"""
    
    print("🔍 Testing YouTube Service...")
    
    async with aiohttp.ClientSession() as session:
        
        # Test health check
        print("\n1. Testing health check...")
        try:
            async with session.get(f"{YOUTUBE_SERVICE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data['status']}")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
        
        # Test get completed streams
        print(f"\n2. Getting completed streams for {CHANNEL_HANDLE}...")
        try:
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/streams/channel/{CHANNEL_ID}/completed"
            params = {
                "max_results": MAX_RESULTS,
                "include_transcripts": True
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Found {data['count']} completed streams")
                    print(f"📊 Transcripts available: {data.get('transcripts_available', 0)}")
                    
                    # Print stream details
                    for i, stream in enumerate(data['streams'][:3], 1):
                        print(f"\n   Stream {i}:")
                        print(f"   📺 Title: {stream['title'][:80]}...")
                        print(f"   🆔 Video ID: {stream['video_id']}")
                        print(f"   📅 Published: {stream['published_at']}")
                        print(f"   👀 Views: {stream['view_count']:,}")
                        print(f"   📝 Has transcript: {stream.get('has_transcript', False)}")
                    
                    return data['streams']
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to get streams: {response.status}")
                    print(f"   Error: {error_data}")
                    return []
        except Exception as e:
            print(f"❌ Error getting streams: {e}")
            return []


async def test_digest_service(streams: List[Dict]):
    """Test digest service with stream transcripts"""
    
    print("\n🤖 Testing Digest Service...")
    
    if not streams:
        print("❌ No streams to test digest generation")
        return
    
    # Find a stream with transcript
    stream_with_transcript = None
    for stream in streams:
        if stream.get('has_transcript') and stream.get('transcript'):
            stream_with_transcript = stream
            break
    
    if not stream_with_transcript:
        print("❌ No streams with transcripts found")
        return
    
    async with aiohttp.ClientSession() as session:
        
        # Test health check
        print("\n1. Testing digest service health...")
        try:
            async with session.get(f"{DIGEST_SERVICE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Digest service healthy: {data['status']}")
                else:
                    print(f"❌ Digest service health check failed: {response.status}")
                    return
        except Exception as e:
            print(f"❌ Digest service health error: {e}")
            return
        
        # Test digest generation
        print(f"\n2. Generating digest for: {stream_with_transcript['title'][:50]}...")
        
        # Prepare transcript text
        transcript_segments = stream_with_transcript['transcript']
        transcript_text = ' '.join([seg['text'] for seg in transcript_segments])
        
        # Prepare request
        digest_request = {
            "video_id": stream_with_transcript['video_id'],
            "transcript": transcript_text[:8000],  # Truncate if too long
            "metadata": {
                "channel_name": stream_with_transcript['channel_title'],
                "video_title": stream_with_transcript['title'],
                "stream_date": stream_with_transcript['published_at'],
                "view_count": stream_with_transcript['view_count']
            },
            "focus_areas": "Financial insights, investment advice, market analysis",
            "ai_providers": ["openai"]
        }
        
        try:
            async with session.post(
                f"{DIGEST_SERVICE_URL}/api/v1/digests/generate",
                json=digest_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Digest generated successfully!")
                    print(f"\n📊 {data['title']}")
                    print(f"Quality Score: {data['quality_score']}/100")
                    print(f"AI Model: {data['ai_model']}")
                    print(f"Processing Time: {data['processing_time']:.2f}s")
                    print(f"Tokens Used: {data['tokens_used']}")
                    
                    print(f"\n📝 Bullet Points:")
                    for i, bullet in enumerate(data['bullet_points'], 1):
                        print(f"   {i}. {bullet['text']}")
                        print(f"      (Words: {bullet['word_count']}, Has numbers: {bullet['has_numbers']})")
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Digest generation failed: {response.status}")
                    print(f"   Error: {error_data}")
                    
        except Exception as e:
            print(f"❌ Error generating digest: {e}")


async def test_transcript_extraction():
    """Test standalone transcript extraction"""
    
    print("\n📝 Testing Transcript Extraction...")
    
    # Test with a known video ID (you might need to replace this)
    test_video_id = "dQw4w9WgXcQ"  # Rick Roll video - should have transcript
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{YOUTUBE_SERVICE_URL}/api/v1/transcripts/{test_video_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Transcript extracted successfully!")
                    print(f"   Segments: {data['segment_count']}")
                    print(f"   Duration: {data['total_duration']:.2f}s")
                    print(f"   Language: {data['language']}")
                    print(f"   Auto-generated: {data['is_auto_generated']}")
                    
                    # Show first few segments
                    print(f"\n   First 3 segments:")
                    for i, segment in enumerate(data['transcript'][:3], 1):
                        print(f"   {i}. [{segment['start']:.1f}s] {segment['text']}")
                
                elif response.status == 404:
                    print(f"⚠️  No transcript available for test video")
                else:
                    error_data = await response.text()
                    print(f"❌ Transcript extraction failed: {response.status}")
                    print(f"   Error: {error_data}")
                    
        except Exception as e:
            print(f"❌ Error testing transcript extraction: {e}")


async def main():
    """Main test function"""
    
    print("🚀 YouTube Digest Backend API Test")
    print(f"Testing channel: {CHANNEL_HANDLE} (ID: {CHANNEL_ID})")
    print("=" * 60)
    
    # Test YouTube service
    streams = await test_youtube_service()
    
    # Test transcript extraction
    await test_transcript_extraction()
    
    # Test digest service
    await test_digest_service(streams)
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")
    
    if streams:
        print(f"\n💡 Next steps:")
        print(f"   - Review the {len(streams)} streams found")
        print(f"   - Check transcript quality and availability")
        print(f"   - Verify digest generation quality scores")
        print(f"   - Monitor API performance and response times")


if __name__ == "__main__":
    # Check if services are running
    print("📋 Prerequisites:")
    print("   1. YouTube service running on http://localhost:8001")
    print("   2. Digest service running on http://localhost:8002")
    print("   3. API keys configured in .env file")
    print("   4. Database and Redis services running")
    print("\nStarting tests in 3 seconds...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)