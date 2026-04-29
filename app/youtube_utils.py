import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.errors
from flask import session
from googleapiclient.http import MediaFileUpload


def build_youtube_api():
    token = session['google_token']
    credentials = google.oauth2.credentials.Credentials(
        token['token'],
        refresh_token=token.get('refresh_token'),
        token_uri=token['token_uri'],
        client_id=token['client_id'],
        client_secret=token['client_secret'],
        scopes=token['scopes'],
    )
    return googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)


def paginated(resource, method_name, **kwargs):
    items = []
    page_token = None
    method = getattr(resource, method_name)
    while True:
        params = dict(kwargs)
        if page_token:
            params['pageToken'] = page_token
        response = method(**params).execute()
        items.extend(response.get('items', []))
        page_token = response.get('nextPageToken')
        if not page_token:
            return items


def get_my_channel(youtube):
    response = youtube.channels().list(part='id,snippet,contentDetails', mine=True).execute()
    if not response.get('items'):
        return None
    item = response['items'][0]
    return {
        'id': item['id'],
        'title': item['snippet'].get('title', 'YouTube user'),
        'thumbnail': item['snippet'].get('thumbnails', {}).get('default', {}).get('url'),
        'uploads_playlist_id': item['contentDetails']['relatedPlaylists'].get('uploads'),
    }


def list_my_videos(youtube):
    channel = get_my_channel(youtube)
    playlist_id = channel.get('uploads_playlist_id') if channel else None
    if not playlist_id:
        return []
    items = paginated(youtube.playlistItems(), 'list', part='snippet,contentDetails', playlistId=playlist_id, maxResults=50)
    return [{
        'id': item['contentDetails']['videoId'],
        'title': item['snippet'].get('title', ''),
        'description': item['snippet'].get('description', ''),
        'thumbnail': item['snippet'].get('thumbnails', {}).get('default', {}).get('url'),
    } for item in items]


def list_rated_videos(youtube, rating):
    items = paginated(youtube.videos(), 'list', part='id,snippet', myRating=rating, maxResults=50)
    return [{
        'id': item['id'],
        'title': item['snippet'].get('title', ''),
        'description': item['snippet'].get('description', ''),
        'channel_title': item['snippet'].get('channelTitle', ''),
        'thumbnail': item['snippet'].get('thumbnails', {}).get('default', {}).get('url'),
    } for item in items]


def list_my_likes(youtube):
    return list_rated_videos(youtube, 'like')


def list_my_dislikes(youtube):
    return list_rated_videos(youtube, 'dislike')


def list_channel_comments(youtube, only_author_channel_id=None):
    channel = get_my_channel(youtube)
    if not channel:
        return []
    try:
        items = paginated(youtube.commentThreads(), 'list', part='snippet', allThreadsRelatedToChannelId=channel['id'], maxResults=50, textFormat='plainText')
    except googleapiclient.errors.HttpError:
        return []
    comments = []
    for item in items:
        comment = item['snippet']['topLevelComment']
        snippet = comment['snippet']
        author_channel_id = snippet.get('authorChannelId', {}).get('value')
        if only_author_channel_id and author_channel_id != only_author_channel_id:
            continue
        comments.append({
            'id': comment['id'],
            'text': snippet.get('textDisplay') or snippet.get('textOriginal', ''),
            'video_id': snippet.get('videoId', ''),
            'video_title': item['snippet'].get('videoTitle', ''),
            'author': snippet.get('authorDisplayName', ''),
            'published_at': snippet.get('publishedAt', ''),
        })
    return comments


def list_my_comments(youtube):
    channel = get_my_channel(youtube)
    return list_channel_comments(youtube, channel['id']) if channel else []


def list_comments_on_my_videos(youtube):
    return list_channel_comments(youtube)


def list_my_playlists(youtube):
    items = paginated(youtube.playlists(), 'list', part='snippet,contentDetails', mine=True, maxResults=50)
    return [{
        'id': item['id'],
        'title': item['snippet'].get('title', ''),
        'description': item['snippet'].get('description', ''),
        'video_count': item.get('contentDetails', {}).get('itemCount', 0),
    } for item in items]


def upload_to_youtube(youtube, title, description, filepath, privacy_status, tags, category_id, made_for_kids):
    body = {
        'snippet': {'title': title, 'description': description, 'tags': [t.strip() for t in tags.split(',') if t.strip()], 'categoryId': category_id},
        'status': {'privacyStatus': privacy_status, 'selfDeclaredMadeForKids': made_for_kids},
    }
    media = MediaFileUpload(filepath, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response


def delete_comment(youtube, comment_id):
    youtube.comments().delete(id=comment_id).execute()


def delete_video(youtube, video_id):
    youtube.videos().delete(id=video_id).execute()


def clear_video_rating(youtube, video_id):
    youtube.videos().rate(id=video_id, rating='none').execute()


def delete_playlist(youtube, playlist_id):
    youtube.playlists().delete(id=playlist_id).execute()
