#!/usr/bin/env python3
"""
Test the complete end-to-end pipeline: Transcript extraction → LLM processing → Digest generation
"""

import asyncio
import aiohttp
import json
import sys

# Configuration
YOUTUBE_SERVICE_URL = "http://localhost:8001"
DIGEST_SERVICE_URL = "http://localhost:8002"
CHANNEL_HANDLE = "@amitinvesting"

# Test video from @amitinvesting
TEST_VIDEO_ID = "LYKDXu3Ph_w"  # TRUMP GETS AN EU DEAL


async def test_transcript_extraction():
    """Test transcript extraction from YouTube service"""
    
    print("📝 Step 1: Testing Transcript Extraction")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{YOUTUBE_SERVICE_URL}/api/v1/transcripts/{TEST_VIDEO_ID}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Transcript extracted successfully!")
                    print(f"   Video ID: {data['video_id']}")
                    print(f"   Segments: {data['segment_count']}")
                    print(f"   Duration: {data['total_duration']:.1f} seconds")
                    print(f"   Language: {data['language']}")
                    
                    # Calculate transcript stats
                    total_words = sum(len(seg['text'].split()) for seg in data['transcript'])
                    print(f"   Total words: {total_words:,}")
                    
                    # Show sample content
                    print(f"   Sample content: {data['transcript'][0]['text'][:80]}...")
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to extract transcript: HTTP {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


async def test_digest_generation(transcript_data):
    """Test digest generation from transcript"""
    
    if not transcript_data:
        print(f"\n⚠️  Skipping digest test - no transcript data")
        return None
    
    print(f"\n🤖 Step 2: Testing Digest Generation")
    print("=" * 50)
    
    # Prepare transcript text
    transcript_text = ' '.join([seg['text'] for seg in transcript_data['transcript']])
    
    # Create digest request
    digest_request = {
        "video_id": transcript_data['video_id'],
        "transcript": transcript_text,
        "metadata": {
            "channel_name": "Amit Kukreja",
            "video_title": "TRUMP GETS AN EU DEAL - Market Analysis",
            "stream_date": "2025-07-28",
            "view_count": 34446,
            "duration": transcript_data['total_duration']
        },
        "focus_areas": "Trump EU deal impact, Tesla Samsung partnership, NVIDIA AI growth, market sentiment",
        "ai_providers": ["openai"]
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DIGEST_SERVICE_URL}/api/v1/digests/generate"
            
            print(f"🎯 Sending transcript ({len(transcript_text)} chars) to AI...")
            
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
                    print(f"Confidence: {data['confidence_score']:.2f}")
                    
                    print(f"\n📝 Generated Bullet Points:")
                    for i, bullet in enumerate(data['bullet_points'], 1):
                        print(f"   {i}. {bullet['text']}")
                        print(f"      📊 Words: {bullet['word_count']}, Has numbers: {bullet['has_numbers']}")
                    
                    print(f"\n📄 Raw Digest:")
                    print(f"{data['raw_digest']}")
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Digest generation failed: HTTP {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


async def test_end_to_end_pipeline():
    """Test the complete end-to-end pipeline"""
    
    print(f"\n🚀 Step 3: Testing End-to-End Pipeline")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DIGEST_SERVICE_URL}/api/v1/pipeline/process-stream/{TEST_VIDEO_ID}"
            params = {
                "channel_name": "Amit Kukreja (@amitinvesting)",
                "focus_areas": "EU trade deal impact, Tesla partnerships, NVIDIA growth, Federal Reserve policy, market outlook"
            }
            
            print(f"🎯 Processing complete pipeline for video {TEST_VIDEO_ID}...")
            print(f"   This will: Extract transcript → Process with AI → Generate digest")
            
            async with session.post(url, params=params) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ End-to-end pipeline completed successfully!")
                    print(f"\n📊 Final Digest:")
                    print(f"Title: {data['title']}")
                    print(f"Quality Score: {data['quality_score']}/100")
                    print(f"Processing Time: {data['processing_time']:.2f}s")
                    
                    print(f"\n📝 Bullet Points:")
                    for i, bullet in enumerate(data['bullet_points'], 1):
                        print(f"   {i}. {bullet['text']}")
                    
                    # Show metadata
                    if data.get('metadata'):
                        print(f"\n📊 Metadata:")
                        for key, value in data['metadata'].items():
                            print(f"   {key}: {value}")
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Pipeline failed: HTTP {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


async def test_channel_processing():
    """Test processing multiple streams from @amitinvesting channel"""
    
    print(f"\n📺 Step 4: Testing Channel Processing")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DIGEST_SERVICE_URL}/api/v1/pipeline/process-channel/{CHANNEL_HANDLE}"
            params = {
                "max_streams": 3,
                "focus_areas": "Market analysis, stock movements, trading opportunities, economic policy impact"
            }
            
            print(f"🎯 Processing {params['max_streams']} streams from {CHANNEL_HANDLE}...")
            
            async with session.post(url, params=params) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Channel processing completed!")
                    print(f"   Processed {len(data)} streams")
                    
                    successful_digests = [d for d in data if not d.get('error')]
                    print(f"   Successful digests: {len(successful_digests)}")
                    
                    # Show each digest
                    for i, digest in enumerate(successful_digests, 1):
                        print(f"\n   📊 Digest {i}: {digest['title']}")
                        print(f"      Video ID: {digest['video_id']}")
                        print(f"      Quality: {digest['quality_score']}/100")
                        print(f"      Bullet points: {len(digest['bullet_points'])}")
                    
                    return data
                    
                else:
                    error_data = await response.text()
                    print(f"❌ Channel processing failed: HTTP {response.status}")
                    print(f"   Error: {error_data}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


async def test_service_health():
    """Test that both services are running"""
    
    print("🏥 Testing Service Health")
    print("=" * 30)
    
    services = [
        ("YouTube Service", f"{YOUTUBE_SERVICE_URL}/health"),
        ("Digest Service", f"{DIGEST_SERVICE_URL}/health")
    ]
    
    all_healthy = True
    
    async with aiohttp.ClientSession() as session:
        for name, url in services:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ {name}: {data['status']}")
                    else:
                        print(f"❌ {name}: HTTP {response.status}")
                        all_healthy = False
                        
            except Exception as e:
                print(f"❌ {name}: Connection failed - {e}")
                all_healthy = False
    
    return all_healthy


async def main():
    """Main test function"""
    
    print("🚀 YouTube Digest Backend - End-to-End Pipeline Test")
    print("Testing: Transcript Extraction → LLM Processing → Digest Generation")
    print("=" * 80)
    
    # Test service health first
    services_healthy = await test_service_health()
    
    if not services_healthy:
        print(f"\n❌ Services not healthy. Please start both services:")
        print(f"   Terminal 1: uv run uvicorn services.youtube-service.app.main:app --port 8001 --reload")
        print(f"   Terminal 2: uv run uvicorn services.digest-service.app.main:app --port 8002 --reload")
        return
    
    # Test individual components
    transcript_data = await test_transcript_extraction()
    digest_data = await test_digest_generation(transcript_data)
    
    # Test end-to-end pipeline
    pipeline_data = await test_end_to_end_pipeline()
    
    # Test channel processing
    channel_data = await test_channel_processing()
    
    print(f"\n" + "=" * 80)
    print(f"📋 Pipeline Test Summary")
    
    results = {
        "Transcript Extraction": "✅" if transcript_data else "❌",
        "Digest Generation": "✅" if digest_data else "❌",
        "End-to-End Pipeline": "✅" if pipeline_data else "❌",
        "Channel Processing": "✅" if channel_data else "❌"
    }
    
    for test, status in results.items():
        print(f"   {status} {test}")
    
    success_count = sum(1 for status in results.values() if status == "✅")
    
    print(f"\n📊 Results: {success_count}/{len(results)} tests passed")
    
    if success_count == len(results):
        print(f"🎉 Complete pipeline working perfectly!")
        print(f"\n💡 The system successfully:")
        print(f"   • Extracts transcripts from @amitinvesting live streams")
        print(f"   • Processes transcript content with AI/LLM")
        print(f"   • Generates Robinhood Cortex-style financial digests")
        print(f"   • Handles both single videos and batch channel processing")
        
        if pipeline_data:
            print(f"\n🎯 Example Pipeline Output:")
            print(f"   Title: {pipeline_data['title']}")
            print(f"   Quality Score: {pipeline_data['quality_score']}/100")
            print(f"   Processing Time: {pipeline_data['processing_time']:.2f}s")
        
        print(f"\n🔗 Available Endpoints:")
        print(f"   • Single video: POST /api/v1/pipeline/process-stream/{TEST_VIDEO_ID}")
        print(f"   • Channel batch: POST /api/v1/pipeline/process-channel/@amitinvesting")
        
    else:
        print(f"⚠️  Some pipeline components need attention")


if __name__ == "__main__":
    print("📋 Prerequisites:")
    print("   1. YouTube service running on port 8001")
    print("   2. Digest service running on port 8002") 
    print("   3. YouTube API key configured")
    print("   4. OpenAI API key configured (optional - will use mock)")
    print("\nStarting end-to-end pipeline tests...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)