#!/usr/bin/env python3
"""
Test the updated YouTube Digest Backend with @amitinvesting channel
Tests the corrected API implementation with real data
"""

import asyncio
import aiohttp
import json
import sys
import os

# Test configuration
YOUTUBE_SERVICE_URL = "http://localhost:8001"
DIGEST_SERVICE_URL = "http://localhost:8002"
CHANNEL_HANDLE = "@amitinvesting"
MAX_RESULTS = 5


async def test_channel_resolution():
    """Test the new channel resolution endpoint"""
    
    print("🔍 Testing Channel Resolution...")
    print("=" * 40)
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/streams/resolve/{CHANNEL_HANDLE}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Handle resolved successfully!")
                    print(f"   Handle: {data['handle']}")
                    print(f"   Channel ID: {data['channel_id']}")
                    print(f"   Title: {data['channel_info']['title']}")
                    print(f"   Subscribers: {data['channel_info']['subscriber_count']:,}")
                    print(f"   Videos: {data['channel_info']['video_count']:,}")
                    print(f"   Total Views: {data['channel_info']['view_count']:,}")
                    
                    return data['channel_id']
                else:
                    error_data = await response.text()
                    print(f"❌ Resolution failed: {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error testing channel resolution: {e}")
            return None


async def test_live_streams_with_handle():
    """Test getting live streams using handle (not channel ID)"""
    
    print(f"\n📺 Testing Live Streams with Handle...")
    print("=" * 40)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test with handle instead of channel ID
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/streams/channel/{CHANNEL_HANDLE}/completed"
            params = {
                "max_results": MAX_RESULTS,
                "include_transcripts": True
            }
            
            print(f"🎯 Requesting: {url}")
            print(f"📊 Parameters: {params}")
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ API call successful!")
                    print(f"   Handle: {data['channel_identifier']}")
                    print(f"   Resolved Channel ID: {data['channel_id']}")
                    print(f"   Streams found: {data['count']}")
                    print(f"   Transcripts available: {data['transcripts_available']}")
                    print(f"   Success rate: {data['transcript_success_rate']}")
                    
                    # Show stream details
                    for i, stream in enumerate(data['streams'][:3], 1):
                        print(f"\n   Stream {i}: {stream['title'][:60]}...")
                        print(f"      🆔 Video ID: {stream['video_id']}")
                        print(f"      👀 Views: {stream['view_count']:,}")
                        print(f"      📝 Has transcript: {stream['has_transcript']}")
                        
                        if stream.get('transcript_stats'):
                            stats = stream['transcript_stats']
                            print(f"      📊 Transcript: {stats['segment_count']} segments, {stats['total_words']} words")
                    
                    return data['streams']
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to get streams: {response.status}")
                    print(f"   Error: {error_data}")
                    return []
                    
        except Exception as e:
            print(f"❌ Error testing live streams: {e}")
            return []


async def test_individual_video_info():
    """Test getting info for a specific video"""
    
    print(f"\n📹 Testing Individual Video Info...")
    print("=" * 40)
    
    # Use a known video ID from @amitinvesting
    test_video_id = "LYKDXu3Ph_w"  # Recent stream from our earlier test
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/streams/{test_video_id}/info"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Video info retrieved!")
                    print(f"   Title: {data['title'][:80]}...")
                    print(f"   Channel: {data['channel_title']}")
                    print(f"   Published: {data['published_at']}")
                    print(f"   Duration: {data['duration']}")
                    print(f"   Views: {data['view_count']:,}")
                    print(f"   Likes: {data['like_count']:,}")
                    print(f"   Is Live Stream: {data['is_live_stream']}")
                    
                    if data.get('live_streaming_details'):
                        live = data['live_streaming_details']
                        print(f"   🔴 Start Time: {live.get('actual_start_time')}")
                        print(f"   ⏹️  End Time: {live.get('actual_end_time')}")
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to get video info: {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error testing video info: {e}")
            return None


async def test_transcript_extraction():
    """Test transcript extraction endpoint"""
    
    print(f"\n📝 Testing Transcript Extraction...")
    print("=" * 40)
    
    test_video_id = "LYKDXu3Ph_w"  # Recent stream
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/transcripts/{test_video_id}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Transcript extracted!")
                    print(f"   Video ID: {data['video_id']}")
                    print(f"   Segments: {data['segment_count']}")
                    print(f"   Duration: {data['total_duration']:.2f}s")
                    print(f"   Language: {data['language']}")
                    print(f"   Auto-generated: {data['is_auto_generated']}")
                    
                    # Show first few segments
                    print(f"\n   First 3 segments:")
                    for i, segment in enumerate(data['transcript'][:3], 1):
                        print(f"   {i}. [{segment['start']:.1f}s] {segment['text'][:50]}...")
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to extract transcript: {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error testing transcript extraction: {e}")
            return None


async def test_digest_generation(transcript_data):
    """Test digest generation with real transcript data"""
    
    if not transcript_data:
        print(f"\n⚠️  Skipping digest test - no transcript data")
        return
    
    print(f"\n🤖 Testing Digest Generation...")
    print("=" * 40)
    
    # Prepare transcript text
    transcript_text = ' '.join([seg['text'] for seg in transcript_data['transcript']])
    
    # Prepare digest request
    digest_request = {
        "video_id": transcript_data['video_id'],
        "transcript": transcript_text[:8000],  # Truncate if too long
        "metadata": {
            "channel_name": "Amit Kukreja",
            "video_title": "Market Analysis Live Stream",
            "stream_date": "2025-07-28",
            "view_count": 30000
        },
        "focus_areas": "Financial insights, stock market analysis, investment advice",
        "ai_providers": ["openai"]
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DIGEST_SERVICE_URL}/api/v1/digests/generate"
            
            async with session.post(
                url,
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
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Digest generation failed: {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error testing digest generation: {e}")
            return None


async def test_health_checks():
    """Test health endpoints"""
    
    print(f"\n🏥 Testing Health Checks...")
    print("=" * 40)
    
    services = [
        ("YouTube Service", f"{YOUTUBE_SERVICE_URL}/health"),
        ("Digest Service", f"{DIGEST_SERVICE_URL}/health")
    ]
    
    async with aiohttp.ClientSession() as session:
        for name, url in services:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ {name}: {data['status']}")
                    else:
                        print(f"❌ {name}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"❌ {name}: Connection failed - {e}")


async def main():
    """Main test function"""
    
    print("🚀 Updated YouTube Digest Backend Test")
    print(f"Testing with: {CHANNEL_HANDLE}")
    print("=" * 60)
    
    # Test health checks first
    await test_health_checks()
    
    # Test channel resolution
    channel_id = await test_channel_resolution()
    
    # Test live streams with handle
    streams = await test_live_streams_with_handle()
    
    # Test individual video info
    video_info = await test_individual_video_info()
    
    # Test transcript extraction
    transcript_data = await test_transcript_extraction()
    
    # Test digest generation (if we have transcript data)
    digest_data = await test_digest_generation(transcript_data)
    
    print("\n" + "=" * 60)
    print("🏁 Test Summary")
    
    results = {
        "Channel Resolution": "✅" if channel_id else "❌",
        "Live Streams": "✅" if streams else "❌",
        "Video Info": "✅" if video_info else "❌",
        "Transcript Extraction": "✅" if transcript_data else "❌",
        "Digest Generation": "✅" if digest_data else "❌"
    }
    
    for test, status in results.items():
        print(f"   {status} {test}")
    
    success_count = sum(1 for status in results.values() if status == "✅")
    total_tests = len(results)
    
    print(f"\n📊 Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print(f"🎉 All systems working perfectly!")
        print(f"\n💡 Backend is ready for production use:")
        print(f"   • Handle resolution: @amitinvesting → {channel_id}")
        print(f"   • Live stream detection: {len(streams) if streams else 0} streams found")
        print(f"   • Transcript extraction: Working")
        print(f"   • AI digest generation: Working")
    else:
        print(f"⚠️  Some tests failed - check service status and configuration")


if __name__ == "__main__":
    print("📋 Prerequisites:")
    print("   1. YouTube service running: uv run uvicorn services.youtube-service.app.main:app --port 8001 --reload")
    print("   2. Digest service running: uv run uvicorn services.digest-service.app.main:app --port 8002 --reload")
    print("   3. API keys configured in .env file")
    print("   4. Dependencies installed: uv sync")
    print("\nStarting tests in 3 seconds...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)