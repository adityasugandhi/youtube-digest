#!/usr/bin/env python3
"""
Test getting recent 5 live streams from @amitinvesting channel
"""

import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import json

# API Configuration
YOUTUBE_API_KEY = "AIzaSyDARqb_bv3lgd2XadzaeBYKp4P4kJhpwtc"
CHANNEL_ID = "UCjZnbgPb08NFg7MHyPQRZ3Q"  # @amitinvesting
MAX_RESULTS = 5


def get_recent_live_streams():
    """Get recent completed live streams from @amitinvesting"""
    
    print("📺 Getting recent live streams from @amitinvesting")
    print("=" * 60)
    print(f"Channel ID: {CHANNEL_ID}")
    print(f"Requesting: {MAX_RESULTS} recent streams")
    print()
    
    try:
        # Initialize YouTube API
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # Method 1: Search for videos from the channel (broader search)
        print("🔍 Method 1: Searching for recent videos...")
        search_response = youtube.search().list(
            part='snippet',
            channelId=CHANNEL_ID,
            type='video',
            order='date',
            maxResults=50  # Get more to filter for live streams
        ).execute()
        
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        print(f"   Found {len(video_ids)} recent videos")
        
        if not video_ids:
            print("❌ No videos found")
            return
        
        # Get detailed information about these videos
        print("\n📋 Getting detailed video information...")
        videos_response = youtube.videos().list(
            part='snippet,liveStreamingDetails,statistics,contentDetails',
            id=','.join(video_ids)
        ).execute()
        
        # Filter for live streams
        live_streams = []
        regular_videos = []
        
        for item in videos_response['items']:
            if 'liveStreamingDetails' in item:
                live_streams.append(item)
            else:
                regular_videos.append(item)
        
        print(f"   📺 Total videos analyzed: {len(videos_response['items'])}")
        print(f"   🔴 Live streams found: {len(live_streams)}")
        print(f"   📹 Regular videos: {len(regular_videos)}")
        
        # Display live streams
        if live_streams:
            print(f"\n🎯 Recent Live Streams (showing up to {MAX_RESULTS}):")
            print("=" * 60)
            
            for i, stream in enumerate(live_streams[:MAX_RESULTS], 1):
                snippet = stream['snippet']
                live_details = stream['liveStreamingDetails']
                stats = stream['statistics']
                content = stream['contentDetails']
                
                print(f"\n{i}. {snippet['title']}")
                print(f"   🆔 Video ID: {stream['id']}")
                print(f"   📅 Published: {snippet['publishedAt']}")
                view_count = stats.get('viewCount', 'Unknown')
                like_count = stats.get('likeCount', 'Unknown')
                comment_count = stats.get('commentCount', 'Unknown')
                
                # Format numbers with commas if they're numeric
                if view_count != 'Unknown':
                    view_count = f"{int(view_count):,}"
                if like_count != 'Unknown':
                    like_count = f"{int(like_count):,}"
                if comment_count != 'Unknown':
                    comment_count = f"{int(comment_count):,}"
                
                print(f"   👀 Views: {view_count}")
                print(f"   👍 Likes: {like_count}")
                print(f"   💬 Comments: {comment_count}")
                print(f"   ⏱️  Duration: {content.get('duration', 'Unknown')}")
                
                # Live streaming details
                if live_details.get('actualStartTime'):
                    start_time = live_details['actualStartTime']
                    print(f"   🔴 Started: {start_time}")
                
                if live_details.get('actualEndTime'):
                    end_time = live_details['actualEndTime']
                    print(f"   ⏹️  Ended: {end_time}")
                
                # Check for concurrent viewers (if available)
                if live_details.get('concurrentViewers'):
                    concurrent = int(live_details['concurrentViewers'])
                    print(f"   👥 Peak viewers: {concurrent:,}")
                
                # Description preview
                description = snippet['description'][:150] + "..." if len(snippet['description']) > 150 else snippet['description']
                print(f"   📝 Description: {description}")
                
                print(f"   🔗 URL: https://www.youtube.com/watch?v={stream['id']}")
        
        else:
            print("\n⚠️  No completed live streams found in recent videos")
            print("This could mean:")
            print("   • Channel doesn't do live streams")
            print("   • No recent live streams")
            print("   • Live streams are scheduled but not completed")
            
            # Show some recent regular videos for reference
            print(f"\n📹 Recent regular videos (for reference):")
            for i, video in enumerate(regular_videos[:3], 1):
                snippet = video['snippet']
                stats = video['statistics']
                print(f"\n   {i}. {snippet['title'][:60]}...")
                print(f"      📅 {snippet['publishedAt']}")
                view_count = stats.get('viewCount', 'Unknown')
                if view_count != 'Unknown':
                    view_count = f"{int(view_count):,}"
                print(f"      👀 {view_count} views")
        
        # Method 2: Try searching specifically for live streams
        print(f"\n🔍 Method 2: Searching specifically for live content...")
        try:
            live_search = youtube.search().list(
                part='snippet',
                channelId=CHANNEL_ID,
                type='video',
                eventType='completed',  # Completed live streams
                order='date',
                maxResults=MAX_RESULTS
            ).execute()
            
            if live_search.get('items'):
                print(f"   ✅ Found {len(live_search['items'])} completed live streams via eventType search")
            else:
                print(f"   ❌ No completed live streams found via eventType search")
                
        except HttpError as e:
            print(f"   ❌ Live stream search failed: {e}")
        
        return live_streams
        
    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def test_transcript_availability(video_ids):
    """Test if transcripts are available for the videos"""
    
    if not video_ids:
        return
    
    print(f"\n📝 Testing transcript availability...")
    print("-" * 40)
    
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        for i, video_id in enumerate(video_ids, 1):
            print(f"{i}. Testing video: {video_id}")
            
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # Try to get English transcript
                try:
                    transcript = transcript_list.find_manually_created_transcript(['en'])
                    print(f"   ✅ Manual English transcript available")
                except:
                    try:
                        transcript = transcript_list.find_generated_transcript(['en'])
                        print(f"   ✅ Auto-generated English transcript available")
                    except:
                        print(f"   ❌ No English transcript available")
                        
            except Exception as e:
                print(f"   ❌ No transcript: {str(e)[:50]}...")
                
    except ImportError:
        print("⚠️  youtube-transcript-api not available for transcript testing")


def main():
    """Main function"""
    
    print("🚀 @amitinvesting Live Streams Analysis")
    print("Channel: Amit Kukreja (@amitinvesting)")
    print("Focus: Recent 5 live streams for transcript extraction")
    print()
    
    # Get live streams
    streams = get_recent_live_streams()
    
    # Test transcript availability
    if streams:
        video_ids = [stream['id'] for stream in streams[:MAX_RESULTS]]
        test_transcript_availability(video_ids)
        
        print(f"\n🎯 Summary:")
        print(f"   📺 Channel: @amitinvesting (Amit Kukreja)")
        print(f"   🔴 Live streams found: {len(streams)}")
        print(f"   👥 Subscribers: 89,700")
        print(f"   📹 Total videos: 3,080")
        print(f"   👀 Total views: 23.8M")
        
        if streams:
            print(f"\n💡 Next steps:")
            print(f"   1. Use video IDs to extract transcripts")
            print(f"   2. Generate financial digests from transcript content")
            print(f"   3. Test API endpoints with these video IDs")
    
    else:
        print("\n❌ No streams available for testing")


if __name__ == "__main__":
    main()