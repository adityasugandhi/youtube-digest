#!/usr/bin/env python3
"""
Focused test for transcript extraction from @amitinvesting live streams
"""

import asyncio
import aiohttp
import json
import sys

# Configuration
YOUTUBE_SERVICE_URL = "http://localhost:8001"
CHANNEL_HANDLE = "@amitinvesting"

# Known video IDs from @amitinvesting (from our earlier tests)
TEST_VIDEO_IDS = [
    "LYKDXu3Ph_w",  # TRUMP GETS AN EU DEAL, TESLA GETS A BIG DEAL
    "olZni1RqMr0",  # HOUSTON, WE HAVE A DEAL
    "u_ZJd6SSCY4",  # PALANTIR IS NOW A TOP 20 COMPANY
    "MaGtwkqJjAM",  # PALANTIR ALL TIME HIGHS
    "52YcNajOXfQ"   # TRUMP & POWELL, CRYPTO SELLS OFF
]


async def test_single_transcript(video_id: str):
    """Test extracting transcript from a single video"""
    
    print(f"\n📝 Testing transcript for video: {video_id}")
    print("-" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/transcripts/{video_id}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Transcript extracted successfully!")
                    print(f"   📊 Segments: {data['segment_count']}")
                    print(f"   ⏱️  Duration: {data['total_duration']:.1f} seconds ({data['total_duration']/3600:.1f} hours)")
                    print(f"   🔤 Language: {data['language']}")
                    print(f"   🤖 Auto-generated: {data['is_auto_generated']}")
                    
                    # Calculate word count
                    total_words = sum(len(seg['text'].split()) for seg in data['transcript'])
                    print(f"   📰 Total words: {total_words:,}")
                    print(f"   📈 Words per minute: {(total_words / (data['total_duration']/60)):.1f}")
                    
                    # Show sample segments
                    print(f"\n   📋 Sample segments:")
                    for i, segment in enumerate(data['transcript'][:5], 1):
                        start_time = f"{int(segment['start']//60):02d}:{int(segment['start']%60):02d}"
                        print(f"   {i}. [{start_time}] {segment['text'][:80]}...")
                    
                    # Show segments with financial keywords
                    financial_keywords = ['stock', 'market', 'trading', 'buy', 'sell', 'price', 'earnings', 'revenue', 'growth']
                    financial_segments = []
                    
                    for segment in data['transcript']:
                        text_lower = segment['text'].lower()
                        if any(keyword in text_lower for keyword in financial_keywords):
                            financial_segments.append(segment)
                    
                    if financial_segments:
                        print(f"\n   💰 Financial content samples ({len(financial_segments)} segments):")
                        for i, segment in enumerate(financial_segments[:3], 1):
                            start_time = f"{int(segment['start']//60):02d}:{int(segment['start']%60):02d}"
                            print(f"   {i}. [{start_time}] {segment['text'][:100]}...")
                    
                    return data
                    
                elif response.status == 404:
                    error_data = await response.json()
                    print(f"❌ No transcript available")
                    print(f"   Reason: {error_data['detail']}")
                    return None
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to extract transcript: HTTP {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


async def test_batch_transcripts():
    """Test batch transcript extraction"""
    
    print(f"\n📦 Testing batch transcript extraction...")
    print("=" * 60)
    
    batch_request = {
        "video_ids": TEST_VIDEO_IDS,
        "concurrent_limit": 3
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/transcripts/batch"
            
            async with session.post(
                url,
                json=batch_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Batch extraction completed!")
                    print(f"   📊 Total requested: {data['total_requested']}")
                    print(f"   ✅ Successful: {data['successful_count']}")
                    print(f"   ❌ Failed: {data['failed_count']}")
                    print(f"   📈 Success rate: {(data['successful_count']/data['total_requested']*100):.1f}%")
                    
                    # Show successful extractions
                    print(f"\n   📝 Successful transcripts:")
                    for i, transcript in enumerate(data['successful'], 1):
                        total_words = sum(len(seg['text'].split()) for seg in transcript['transcript'])
                        duration_hours = transcript['total_duration'] / 3600
                        
                        print(f"   {i}. Video: {transcript['video_id']}")
                        print(f"      Segments: {transcript['segment_count']}")
                        print(f"      Duration: {duration_hours:.1f}h")
                        print(f"      Words: {total_words:,}")
                    
                    # Show failed extractions
                    if data['failed']:
                        print(f"\n   ❌ Failed extractions:")
                        for i, failure in enumerate(data['failed'], 1):
                            print(f"   {i}. Video: {failure['video_id']} - {failure['error']}")
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Batch extraction failed: HTTP {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


async def test_transcripts_with_streams():
    """Test getting streams with transcripts included"""
    
    print(f"\n🎬 Testing streams with transcript inclusion...")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/streams/channel/{CHANNEL_HANDLE}/completed"
            params = {
                "max_results": 3,
                "include_transcripts": True
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Streams with transcripts retrieved!")
                    print(f"   🎥 Streams found: {data['count']}")
                    print(f"   📝 Transcripts available: {data['transcripts_available']}")
                    print(f"   📊 Success rate: {data['transcript_success_rate']}")
                    
                    # Analyze each stream
                    for i, stream in enumerate(data['streams'], 1):
                        print(f"\n   Stream {i}: {stream['title'][:60]}...")
                        print(f"      🆔 Video ID: {stream['video_id']}")
                        print(f"      👀 Views: {stream['view_count']:,}")
                        print(f"      📝 Has transcript: {stream['has_transcript']}")
                        
                        if stream['has_transcript'] and stream.get('transcript_stats'):
                            stats = stream['transcript_stats']
                            print(f"      📊 Transcript stats:")
                            print(f"         Segments: {stats['segment_count']}")
                            print(f"         Duration: {stats['total_duration']/3600:.1f}h")
                            print(f"         Words: {stats['total_words']:,}")
                            
                            # Sample transcript content for financial analysis
                            if stream.get('transcript'):
                                full_text = ' '.join([seg['text'] for seg in stream['transcript'][:10]])
                                print(f"         Sample: {full_text[:100]}...")
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to get streams: HTTP {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


async def analyze_transcript_content(transcript_data):
    """Analyze transcript content for financial insights"""
    
    if not transcript_data:
        return
    
    print(f"\n🔍 Analyzing transcript content for financial insights...")
    print("=" * 60)
    
    # Combine all transcript text
    full_text = ' '.join([seg['text'] for seg in transcript_data['transcript']])
    words = full_text.lower().split()
    
    # Financial keywords to look for
    financial_keywords = {
        'companies': ['tesla', 'nvidia', 'apple', 'microsoft', 'amazon', 'google', 'meta', 'palantir'],
        'market_terms': ['stock', 'market', 'trading', 'buy', 'sell', 'price', 'bullish', 'bearish'],
        'financial_metrics': ['earnings', 'revenue', 'profit', 'growth', 'dividend', 'eps'],
        'economic_terms': ['fed', 'inflation', 'rates', 'gdp', 'unemployment', 'recession']
    }
    
    print(f"📊 Content Analysis:")
    print(f"   Total words: {len(words):,}")
    print(f"   Unique words: {len(set(words)):,}")
    
    # Count financial keywords
    for category, keywords in financial_keywords.items():
        found_keywords = []
        for keyword in keywords:
            count = words.count(keyword)
            if count > 0:
                found_keywords.append(f"{keyword}({count})")
        
        if found_keywords:
            print(f"   {category.title()}: {', '.join(found_keywords[:5])}")
    
    # Find segments with multiple financial keywords
    financial_segments = []
    for segment in transcript_data['transcript']:
        text_lower = segment['text'].lower()
        keyword_count = sum(
            1 for category in financial_keywords.values() 
            for keyword in category 
            if keyword in text_lower
        )
        if keyword_count >= 2:
            financial_segments.append((segment, keyword_count))
    
    # Sort by keyword density
    financial_segments.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n💰 High-value financial segments ({len(financial_segments)} found):")
    for i, (segment, count) in enumerate(financial_segments[:3], 1):
        start_time = f"{int(segment['start']//60):02d}:{int(segment['start']%60):02d}"
        print(f"   {i}. [{start_time}] ({count} keywords) {segment['text'][:120]}...")


async def main():
    """Main test function"""
    
    print("📝 YouTube Transcript Extraction Test")
    print(f"Testing with @amitinvesting live streams")
    print("=" * 70)
    
    # Test 1: Single transcript extraction
    print("🎯 Test 1: Single Transcript Extraction")
    transcript_data = await test_single_transcript(TEST_VIDEO_IDS[0])
    
    # Test 2: Batch transcript extraction
    print("\n🎯 Test 2: Batch Transcript Extraction")
    batch_data = await test_batch_transcripts()
    
    # Test 3: Streams with transcripts
    print("\n🎯 Test 3: Streams with Transcripts")
    streams_data = await test_transcripts_with_streams()
    
    # Test 4: Content analysis
    if transcript_data:
        print("\n🎯 Test 4: Content Analysis")
        await analyze_transcript_content(transcript_data)
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 Test Summary")
    
    results = {
        "Single Transcript": "✅" if transcript_data else "❌",
        "Batch Transcripts": "✅" if batch_data else "❌", 
        "Streams + Transcripts": "✅" if streams_data else "❌"
    }
    
    for test, status in results.items():
        print(f"   {status} {test}")
    
    success_count = sum(1 for status in results.values() if status == "✅")
    
    print(f"\n📊 Results: {success_count}/{len(results)} tests passed")
    
    if success_count == len(results):
        print("🎉 All transcript tests passed!")
        print("\n💡 Key findings:")
        if transcript_data:
            total_words = sum(len(seg['text'].split()) for seg in transcript_data['transcript'])
            print(f"   • Average stream length: {transcript_data['total_duration']/3600:.1f} hours")
            print(f"   • Average word count: {total_words:,} words")
            print(f"   • Rich financial content for AI digest generation")
        
        if batch_data:
            success_rate = (batch_data['successful_count']/batch_data['total_requested']*100)
            print(f"   • Batch extraction success rate: {success_rate:.1f}%")
        
        print(f"   • Ready for AI digest generation!")
    else:
        print("⚠️  Some transcript tests failed")


if __name__ == "__main__":
    print("📋 Prerequisites:")
    print("   1. YouTube service running on port 8001")
    print("   2. Valid YouTube API key in .env")
    print("   3. youtube-transcript-api dependency installed")
    print("\nStarting transcript tests...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)