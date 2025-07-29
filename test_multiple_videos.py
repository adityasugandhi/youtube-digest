#!/usr/bin/env python3
"""
Test transcript extraction with multiple videos to find working ones
"""

from youtube_transcript_api import YouTubeTranscriptApi
import time

# Multiple video IDs to test (including some well-known ones)
TEST_VIDEOS = [
    ("LYKDXu3Ph_w", "@amitinvesting - TRUMP GETS AN EU DEAL"),
    ("olZni1RqMr0", "@amitinvesting - HOUSTON, WE HAVE A DEAL"), 
    ("u_ZJd6SSCY4", "@amitinvesting - PALANTIR IS NOW A TOP 20 COMPANY"),
    ("dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),  # Famous video
    ("9bZkp7q19f0", "PSY - GANGNAM STYLE"),  # Another famous video
]

def test_video_transcript(video_id: str, title: str):
    """Test transcript extraction for a single video"""
    
    print(f"\n📺 Testing: {title}")
    print(f"   Video ID: {video_id}")
    
    try:
        # Check if transcripts are available
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get English transcript
        transcript = None
        transcript_type = "None"
        
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            transcript_type = "Manual"
        except:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
                transcript_type = "Auto-generated"
            except:
                print(f"   ❌ No English transcript available")
                return False
        
        # Fetch the transcript
        transcript_data = transcript.fetch()
        
        if transcript_data and len(transcript_data) > 0:
            total_duration = transcript_data[-1]['start'] + transcript_data[-1]['duration']
            total_words = sum(len(segment['text'].split()) for segment in transcript_data)
            
            print(f"   ✅ SUCCESS ({transcript_type})")
            print(f"      Segments: {len(transcript_data)}")
            print(f"      Duration: {total_duration/60:.1f} minutes")
            print(f"      Words: {total_words:,}")
            print(f"      Sample: {transcript_data[0]['text'][:60]}...")
            
            return True
        else:
            print(f"   ❌ Empty transcript data")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:60]}...")
        return False


def main():
    """Test multiple videos to find working transcript extraction"""
    
    print("🔍 Testing Transcript Extraction with Multiple Videos")
    print("=" * 60)
    
    working_videos = []
    
    for video_id, title in TEST_VIDEOS:
        success = test_video_transcript(video_id, title)
        if success:
            working_videos.append((video_id, title))
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    print(f"\n📊 Results:")
    print(f"   Total tested: {len(TEST_VIDEOS)}")
    print(f"   Working: {len(working_videos)}")
    print(f"   Success rate: {len(working_videos)/len(TEST_VIDEOS)*100:.1f}%")
    
    if working_videos:
        print(f"\n✅ Working videos for backend testing:")
        for video_id, title in working_videos:
            print(f"   • {video_id} - {title[:50]}...")
        
        print(f"\n🚀 Test backend with working video:")
        working_id = working_videos[0][0]
        print(f"   curl http://localhost:8001/api/v1/transcripts/{working_id}")
    else:
        print(f"\n❌ No working transcripts found")
        print(f"   This could indicate:")
        print(f"   • Network connectivity issues")
        print(f"   • YouTube API changes")
        print(f"   • Regional restrictions")


if __name__ == "__main__":
    main()