#!/usr/bin/env python3
"""
Quick test to verify transcript extraction works
"""

import os
import sys
from youtube_transcript_api import YouTubeTranscriptApi

# Test with a known @amitinvesting video
TEST_VIDEO_ID = "LYKDXu3Ph_w"  # Recent stream: TRUMP GETS AN EU DEAL

def test_transcript_extraction():
    """Test if transcript extraction works"""
    
    print("📝 Testing YouTube Transcript Extraction")
    print("=" * 50)
    print(f"Video ID: {TEST_VIDEO_ID}")
    print(f"Channel: @amitinvesting")
    print()
    
    try:
        # List available transcripts
        print("🔍 Checking available transcripts...")
        transcript_list = YouTubeTranscriptApi.list_transcripts(TEST_VIDEO_ID)
        
        available_transcripts = []
        for transcript in transcript_list:
            available_transcripts.append({
                'language': transcript.language,
                'language_code': transcript.language_code,
                'is_generated': transcript.is_generated,
                'is_translatable': transcript.is_translatable
            })
        
        print(f"   Found {len(available_transcripts)} transcript(s):")
        for i, t in enumerate(available_transcripts, 1):
            print(f"   {i}. {t['language']} ({t['language_code']}) - Generated: {t['is_generated']}")
        
        # Try to get English transcript
        print(f"\n📥 Extracting English transcript...")
        
        transcript = None
        try:
            # Try manual first
            transcript = transcript_list.find_manually_created_transcript(['en'])
            print("   ✅ Found manually created English transcript")
        except:
            try:
                # Try auto-generated
                transcript = transcript_list.find_generated_transcript(['en'])
                print("   ✅ Found auto-generated English transcript")
            except:
                print("   ❌ No English transcript available")
                return False
        
        # Fetch transcript data
        if transcript:
            print(f"\n📋 Fetching transcript data...")
            transcript_data = transcript.fetch()
            
            if transcript_data:
                print(f"   ✅ Success! Retrieved {len(transcript_data)} segments")
                
                # Calculate stats
                total_duration = transcript_data[-1]['start'] + transcript_data[-1]['duration']
                total_words = sum(len(segment['text'].split()) for segment in transcript_data)
                
                print(f"   📊 Stats:")
                print(f"      Duration: {total_duration/3600:.1f} hours ({total_duration:.0f} seconds)")
                print(f"      Total words: {total_words:,}")
                print(f"      Words per minute: {(total_words/(total_duration/60)):.1f}")
                
                # Show sample segments
                print(f"\n   📝 Sample segments:")
                for i, segment in enumerate(transcript_data[:5], 1):
                    start_min = int(segment['start'] // 60)
                    start_sec = int(segment['start'] % 60)
                    print(f"   {i}. [{start_min:02d}:{start_sec:02d}] {segment['text'][:80]}...")
                
                # Look for financial keywords
                financial_keywords = ['stock', 'market', 'trading', 'tesla', 'nvidia', 'palantir', 'trump', 'fed']
                financial_segments = []
                
                for segment in transcript_data:
                    text_lower = segment['text'].lower()
                    if any(keyword in text_lower for keyword in financial_keywords):
                        financial_segments.append(segment)
                
                if financial_segments:
                    print(f"\n   💰 Financial content found ({len(financial_segments)} segments):")
                    for i, segment in enumerate(financial_segments[:3], 1):
                        start_min = int(segment['start'] // 60)
                        start_sec = int(segment['start'] % 60)
                        print(f"   {i}. [{start_min:02d}:{start_sec:02d}] {segment['text'][:100]}...")
                
                print(f"\n✅ TRANSCRIPT EXTRACTION WORKS!")
                print(f"   Ready for AI digest generation with {total_words:,} words of content")
                return True
            else:
                print("   ❌ Failed to fetch transcript data")
                return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_transcript_extraction()
    
    if success:
        print(f"\n🎉 Transcript extraction is working perfectly!")
        print(f"🚀 Ready to test the full backend:")
        print(f"   1. Start YouTube service: uv run uvicorn services.youtube-service.app.main:app --port 8001 --reload")
        print(f"   2. Test transcript API: curl http://localhost:8001/api/v1/transcripts/{TEST_VIDEO_ID}")
        print(f"   3. Test with @amitinvesting: curl 'http://localhost:8001/api/v1/streams/channel/@amitinvesting/completed?include_transcripts=true'")
    else:
        print(f"\n❌ Transcript extraction failed")
        print(f"   Check if the video ID {TEST_VIDEO_ID} is correct")
        print(f"   Verify youtube-transcript-api is installed: uv add youtube-transcript-api")