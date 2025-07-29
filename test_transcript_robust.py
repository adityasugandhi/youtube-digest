#!/usr/bin/env python3
"""
Robust transcript extraction test with better error handling
"""

import requests
import json
import time
from urllib.parse import quote

def test_transcript_with_requests(video_id: str):
    """Test transcript extraction using direct HTTP requests"""
    
    print(f"🔍 Testing transcript for {video_id} with HTTP requests...")
    
    try:
        # YouTube transcript endpoint (this is what youtube-transcript-api uses internally)
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"   📡 Fetching video page...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"   ✅ Video page fetched successfully")
            
            # Check if transcript is mentioned in the page
            page_content = response.text
            
            if '"captions"' in page_content or 'captionTracks' in page_content:
                print(f"   ✅ Captions detected in video page")
                return True
            else:
                print(f"   ❌ No captions found in video page")
                return False
        else:
            print(f"   ❌ Failed to fetch video page: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_youtube_transcript_api_fallback():
    """Test youtube-transcript-api with better error handling"""
    
    print(f"\n🔧 Testing youtube-transcript-api with fallback methods...")
    
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
        
        # Test with a known working video
        test_video = "dQw4w9WgXcQ"  # Rick Roll
        
        print(f"   📝 Testing with video: {test_video}")
        
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(test_video)
            print(f"   ✅ Successfully listed transcripts")
            
            # Get available languages
            available_languages = []
            for transcript in transcript_list:
                available_languages.append({
                    'code': transcript.language_code,
                    'name': transcript.language,
                    'generated': transcript.is_generated
                })
            
            print(f"   📋 Available transcripts:")
            for lang in available_languages:
                print(f"      • {lang['name']} ({lang['code']}) - Generated: {lang['generated']}")
            
            # Try to fetch English transcript
            try:
                transcript = transcript_list.find_transcript(['en'])
                transcript_data = transcript.fetch()
                
                if transcript_data:
                    print(f"   ✅ Successfully fetched transcript: {len(transcript_data)} segments")
                    print(f"   📝 Sample: {transcript_data[0]['text'][:50]}...")
                    return True
                else:
                    print(f"   ❌ Empty transcript data")
                    return False
                    
            except Exception as fetch_error:
                print(f"   ❌ Error fetching transcript: {fetch_error}")
                return False
                
        except TranscriptsDisabled:
            print(f"   ❌ Transcripts are disabled for this video")
            return False
        except NoTranscriptFound:
            print(f"   ❌ No transcripts found for this video")
            return False
        except Exception as list_error:
            print(f"   ❌ Error listing transcripts: {list_error}")
            return False
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def test_alternative_approach():
    """Test alternative approaches for transcript extraction"""
    
    print(f"\n🔄 Testing alternative transcript extraction approaches...")
    
    # Method 1: Check if we can access YouTube at all
    try:
        print(f"   🌐 Testing YouTube connectivity...")
        response = requests.get("https://www.youtube.com", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ YouTube is accessible")
        else:
            print(f"   ❌ YouTube returned HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot access YouTube: {e}")
        return False
    
    # Method 2: Try different user agents
    print(f"   🔧 Testing different user agents...")
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'youtube-transcript-api'
    ]
    
    for i, ua in enumerate(user_agents, 1):
        try:
            headers = {'User-Agent': ua}
            response = requests.get("https://www.youtube.com/watch?v=dQw4w9WgXcQ", 
                                  headers=headers, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ User agent {i} works")
                return True
        except:
            continue
    
    print(f"   ❌ All user agents failed")
    return False


def main():
    """Main testing function"""
    
    print("🔍 Comprehensive Transcript Extraction Test")
    print("=" * 60)
    
    # Test 1: Direct HTTP approach
    http_works = test_transcript_with_requests("dQw4w9WgXcQ")
    
    # Test 2: youtube-transcript-api with better error handling
    api_works = test_youtube_transcript_api_fallback()
    
    # Test 3: Alternative approaches
    alt_works = test_alternative_approach()
    
    print(f"\n📊 Test Results:")
    print(f"   HTTP Method: {'✅' if http_works else '❌'}")
    print(f"   YouTube Transcript API: {'✅' if api_works else '❌'}")
    print(f"   Alternative Methods: {'✅' if alt_works else '❌'}")
    
    if api_works:
        print(f"\n🎉 Transcript extraction should work!")
        print(f"📋 Backend transcript endpoints ready:")
        print(f"   • Single: GET /api/v1/transcripts/{video_id}")
        print(f"   • Batch: POST /api/v1/transcripts/batch")
        print(f"   • With streams: GET /api/v1/streams/channel/@amitinvesting/completed?include_transcripts=true")
    else:
        print(f"\n❌ Transcript extraction issues detected")
        print(f"💡 Possible solutions:")
        print(f"   • Check network connectivity")
        print(f"   • Try updating youtube-transcript-api: uv add youtube-transcript-api@latest")
        print(f"   • Check if running behind firewall/proxy")
        print(f"   • Try different video IDs")
        
        print(f"\n🔧 Alternative: Use YouTube Data API v3 captions endpoint")
        print(f"   This requires additional API setup but is more reliable")


if __name__ == "__main__":
    main()