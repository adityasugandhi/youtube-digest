#!/usr/bin/env python3
"""
Test the updated transcript functionality with multiple methods
"""

import asyncio
import sys
import os

# Add project to path
sys.path.append('.')

async def test_transcript_methods():
    """Test the updated transcript extraction methods"""
    
    print("🔍 Testing Updated Transcript Extraction Methods")
    print("=" * 60)
    
    # Import our updated YouTube client
    try:
        from services.youtube_service.app.services.youtube_client import YouTubeClient
        from services.youtube_service.app.core.config import settings
        
        print(f"✅ Successfully imported YouTubeClient")
        print(f"📊 YouTube API Key: {'Set' if settings.youtube_api_key else 'Missing'}")
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Initialize client
    client = YouTubeClient()
    
    # Test video IDs
    test_videos = [
        ("LYKDXu3Ph_w", "@amitinvesting - TRUMP GETS AN EU DEAL"),
        ("dQw4w9WgXcQ", "Rick Roll - Known working video"),
        ("9bZkp7q19f0", "Gangnam Style - Another test")
    ]
    
    for video_id, description in test_videos:
        print(f"\n📹 Testing: {description}")
        print(f"   Video ID: {video_id}")
        
        try:
            transcript = await client.extract_transcript(video_id)
            
            if transcript:
                total_words = sum(len(seg.text.split()) for seg in transcript)
                duration = transcript[-1].end if transcript else 0
                
                print(f"   ✅ SUCCESS!")
                print(f"      Segments: {len(transcript)}")
                print(f"      Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
                print(f"      Words: {total_words:,}")
                print(f"      Sample: {transcript[0].text[:80]}...")
                
                # Check for financial content
                financial_keywords = ['market', 'stock', 'trading', 'tesla', 'trump', 'fed']
                financial_segments = [
                    seg for seg in transcript 
                    if any(keyword in seg.text.lower() for keyword in financial_keywords)
                ]
                
                if financial_segments:
                    print(f"      💰 Financial content: {len(financial_segments)} segments")
                
                return True
            else:
                print(f"   ❌ No transcript available")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return False


async def test_batch_transcripts():
    """Test batch transcript extraction"""
    
    print(f"\n📦 Testing Batch Transcript Extraction")
    print("=" * 60)
    
    try:
        from services.youtube_service.app.services.youtube_client import YouTubeClient
        
        client = YouTubeClient()
        
        # Test with @amitinvesting video IDs
        video_ids = ["LYKDXu3Ph_w", "olZni1RqMr0", "u_ZJd6SSCY4"]
        
        print(f"🎯 Testing batch extraction for {len(video_ids)} videos...")
        
        transcripts = await client.batch_extract_transcripts(video_ids, concurrent_limit=3)
        
        success_count = sum(1 for t in transcripts.values() if t is not None)
        
        print(f"📊 Results:")
        print(f"   Total requested: {len(video_ids)}")
        print(f"   Successful: {success_count}")
        print(f"   Success rate: {success_count/len(video_ids)*100:.1f}%")
        
        for video_id, transcript in transcripts.items():
            if transcript:
                word_count = sum(len(seg.text.split()) for seg in transcript)
                print(f"   ✅ {video_id}: {len(transcript)} segments, {word_count:,} words")
            else:
                print(f"   ❌ {video_id}: No transcript")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Batch test error: {e}")
        return False


async def main():
    """Main test function"""
    
    # Test single transcript extraction
    single_success = await test_transcript_methods()
    
    # Test batch extraction
    batch_success = await test_batch_transcripts()
    
    print(f"\n" + "=" * 60)
    print(f"📋 Final Results")
    
    results = {
        "Single Transcript": single_success,
        "Batch Transcripts": batch_success
    }
    
    for test, success in results.items():
        status = "✅" if success else "❌"
        print(f"   {status} {test}")
    
    if any(results.values()):
        print(f"\n🎉 Transcript extraction is working!")
        print(f"💡 The backend now supports:")
        print(f"   • YouTube Data API v3 captions (primary method)")
        print(f"   • youtube-transcript-api (fallback)")
        print(f"   • Mock transcripts for testing (@amitinvesting videos)")
        print(f"\n🚀 Ready to test full backend:")
        print(f"   1. Start YouTube service: uv run uvicorn services.youtube-service.app.main:app --port 8001 --reload")
        print(f"   2. Test API: curl http://localhost:8001/api/v1/transcripts/LYKDXu3Ph_w")
        print(f"   3. Test with streams: curl 'http://localhost:8001/api/v1/streams/channel/@amitinvesting/completed?include_transcripts=true'")
    else:
        print(f"\n❌ Transcript extraction needs more work")
        print(f"   The mock transcripts will allow testing of other components")


if __name__ == "__main__":
    asyncio.run(main())