import google.oauth2.credentials
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload
from flask import session
from app import CHANNEL_ID

def build_youtube_api():
    credentials = google.oauth2.credentials.Credentials(
        session['google_token']['token'],
        refresh_token=session['google_token'].get('refresh_token'),
        token_uri=session['google_token']['token_uri'],
        client_id=session['google_token']['client_id'],
        client_secret=session['google_token']['client_secret'],
        scopes=session['google_token']['scopes']
    )
    return googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)

def list_my_videos(youtube):
    videos = []
    try:
        request = youtube.channels().list(
            part="contentDetails",
            mine=True
        )
        response = request.execute()
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50
        )
        response = request.execute()
        for item in response['items']:
            video = {
                'id': item['snippet']['resourceId']['videoId'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description']
            }
            videos.append(video)
        while 'nextPageToken' in response:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=response['nextPageToken']
            )
            response = request.execute()
            for item in response['items']:
                video = {
                    'id': item['snippet']['resourceId']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description']
                }
                videos.append(video)
    except Exception as e:
        print(f"An error occurred: {e}")
    return videos

def list_my_comments(youtube):
    comments = []
    try:
        request = youtube.activities().list(
            part="snippet,contentDetails",
            mine=True,
            maxResults=50
        )
        response = request.execute()
        video_ids = set()
        for item in response['items']:
            if 'upload' in item['contentDetails']:
                video_ids.add(item['contentDetails']['upload']['videoId'])
            if 'playlistItem' in item['contentDetails']:
                video_ids.add(item['contentDetails']['playlistItem']['resourceId']['videoId'])
        for video_id in video_ids:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=50,
                textFormat="plainText"
            )
            response = request.execute()
            for item in response['items']:
                top_level_comment = item['snippet']['topLevelComment']
                if top_level_comment['snippet']['authorChannelId']['value'] == CHANNEL_ID:
                    comments.append({
                        'id': top_level_comment['id'],
                        'text': top_level_comment['snippet']['textOriginal'],
                        'video_id': video_id,
                        'published_at': top_level_comment['snippet']['publishedAt']
                    })
            while 'nextPageToken' in response:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=50,
                    pageToken=response['nextPageToken'],
                    textFormat="plainText"
                )
                response = request.execute()
                for item in response['items']:
                    top_level_comment = item['snippet']['topLevelComment']
                    if top_level_comment['snippet']['authorChannelId']['value'] == CHANNEL_ID:
                        comments.append({
                            'id': top_level_comment['id'],
                            'text': top_level_comment['snippet']['textOriginal'],
                            'video_id': video_id,
                            'published_at': top_level_comment['snippet']['publishedAt']
                        })
    except Exception as e:
        print(f"An error occurred: {e}")
    return comments

def list_my_likes(youtube):
    liked_videos = []
    try:
        request = youtube.channels().list(
            part="contentDetails",
            mine=True
        )
        response = request.execute()
        liked_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['likes']
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=liked_playlist_id,
            maxResults=50
        )
        response = request.execute()
        for item in response['items']:
            video = {
                'id': item['snippet']['resourceId']['videoId'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description']
            }
            liked_videos.append(video)
        while 'nextPageToken' in response:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=liked_playlist_id,
                maxResults=50,
                pageToken=response['nextPageToken']
            )
            response = request.execute()
            for item in response['items']:
                video = {
                    'id': item['snippet']['resourceId']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description']
                }
                liked_videos.append(video)
    except Exception as e:
        print(f"An error occurred: {e}")
    return liked_videos

def list_my_saved(youtube):
    saved_playlists = []
    try:
        request = youtube.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50
        )
        response = request.execute()
        for item in response['items']:
            playlist = {
                'id': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description']
            }
            saved_playlists.append(playlist)
        while 'nextPageToken' in response:
            request = youtube.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50,
                pageToken=response['nextPageToken']
            )
            response = request.execute()
            for item in response['items']:
                playlist = {
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description']
                }
                saved_playlists.append(playlist)
    except Exception as e:
        print(f"An error occurred: {e}")
    return saved_playlists

def upload_to_youtube(youtube, title, description, filepath):
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': ['test'],
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'public',
        }
    }
    media = MediaFileUpload(filepath, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if 'id' in response:
            print(f"Video ID '{response['id']}' was successfully uploaded.")
        else:
            print(f"An error occurred: {response}")

def delete_comment(youtube, comment_id):
    try:
        print(f"Attempting to delete comment ID: {comment_id}")
        youtube.comments().delete(id=comment_id).execute()
        print(f"Deleted comment ID: {comment_id}")
    except googleapiclient.errors.HttpError as e:
        print(f"An error occurred: {e}")

def unlike_video(youtube, video_id):
    try:
        youtube.videos().rate(id=video_id, rating='none').execute()
        print(f"Unliked video ID: {video_id}")
    except googleapiclient.errors.HttpError as e:
        print(f"An error occurred: {e}")
