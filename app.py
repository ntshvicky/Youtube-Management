import os
from flask import Flask, redirect, url_for, session, request, render_template, flash
from authlib.integrations.flask_client import OAuth
import google.oauth2.credentials
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload
from werkzeug.utils import secure_filename

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY'  # Replace with your secret key

# OAuth configuration
OAUTH_CLIENT_ID = os.getenv('OAUTH_CLIENT_ID')
OAUTH_CLIENT_SECRET = os.getenv('OAUTH_CLIENT_SECRET')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]

oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=OAUTH_CLIENT_ID,
    client_secret=OAUTH_CLIENT_SECRET,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri='http://localhost:5000/authorized',
    client_kwargs={'scope': ' '.join(SCOPES)}
)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return redirect(url_for('index'))

@app.route('/authorized')
def authorized():
    token = oauth.google.authorize_access_token()
    session['google_token'] = {
        'token': token['access_token'],
        'refresh_token': token.get('refresh_token'),
        'token_uri': 'https://accounts.google.com/o/oauth2/token',
        'client_id': OAUTH_CLIENT_ID,
        'client_secret': OAUTH_CLIENT_SECRET,
        'scopes': SCOPES
    }
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    return render_template('base.html')


@app.route('/my_videos')
def my_videos():
    youtube = build_youtube_api()
    videos = list_my_videos(youtube)
    return render_template('partials/my_videos.html', videos=videos)

@app.route('/my_comments')
def my_comments():
    youtube = build_youtube_api()
    comments = list_my_comments(youtube)
    return render_template('partials/my_comments.html', comments=comments)

@app.route('/my_likes')
def my_likes():
    youtube = build_youtube_api()
    likes = list_my_likes(youtube)
    return render_template('partials/my_likes.html', likes=likes)

@app.route('/my_saved')
def my_saved():
    youtube = build_youtube_api()
    saved = list_my_saved(youtube)
    return render_template('partials/my_saved.html', saved=saved)


@app.route('/delete_comment/<comment_id>')
def delete_comment_route(comment_id):
    youtube = build_youtube_api()
    delete_comment(youtube, comment_id)
    return redirect(url_for('my_comments'))

@app.route('/upload_video', methods=['GET', 'POST'])
def upload_video():
    if request.method == 'POST':
        if 'video_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['video_file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            title = request.form['title']
            description = request.form['description']
            youtube = build_youtube_api()
            upload_to_youtube(youtube, title, description, filepath)
            flash('Video successfully uploaded to YouTube')
            return redirect(url_for('upload_video'))
    return render_template('upload_video.html')

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
        # Step 1: Retrieve the authenticated user's channel details
        request = youtube.channels().list(
            part="contentDetails",
            mine=True
        )
        response = request.execute()

        # Get the playlist ID for the uploads
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Step 2: Retrieve the videos from the uploads playlist
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

        # Paginate through all uploaded videos
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
        # Retrieve activities of the authenticated user
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

        # Retrieve comments made by the authenticated user
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
                if top_level_comment['snippet']['channelId'] == CHANNEL_ID:
                    comments.append({
                        'id': top_level_comment['id'],
                        'text': top_level_comment['snippet']['textOriginal'],
                        'video_id': video_id,
                        'published_at': top_level_comment['snippet']['publishedAt']
                    })

            # Paginate through all comments
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
                    if top_level_comment['snippet']['channelId'] == CHANNEL_ID:
                        comments.append({
                            'id': top_level_comment['id'],
                            'text': top_level_comment['snippet']['textOriginal'],
                            'video_id': video_id,
                            'published_at': top_level_comment['snippet']['publishedAt']
                        })

    except Exception as e:
        print(f"An error occurred: {e}")

    print(f"Total comments collected: {len(comments)}")
    return comments



def list_my_likes(youtube):
    liked_videos = []
    try:
        # Retrieve the authenticated user's liked videos playlist
        request = youtube.channels().list(
            part="contentDetails",
            mine=True
        )
        response = request.execute()

        # Get the playlist ID for liked videos
        liked_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['likes']

        # Retrieve the videos from the liked videos playlist
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

        # Paginate through all liked videos
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
        # Retrieve the authenticated user's saved playlists
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

        # Paginate through all saved playlists
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
            'categoryId': '22'  # See https://developers.google.com/youtube/v3/docs/videoCategories/list
        },
        'status': {
            'privacyStatus': 'public',  # Or 'private' or 'unlisted'
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


@app.route('/delete_selected_comments', methods=['POST'])
def delete_selected_comments():
    youtube = build_youtube_api()
    comment_ids = request.form.getlist('comment_ids')
    for comment_id in comment_ids:
        delete_comment(youtube, comment_id)
    comments = list_my_comments(youtube)
    return render_template('partials/my_comments.html', comments=comments)

@app.route('/delete_selected_likes', methods=['POST'])
def delete_selected_likes():
    youtube = build_youtube_api()
    video_ids = request.form.getlist('video_ids')
    for video_id in video_ids:
        unlike_video(youtube, video_id)
        pass
    likes = list_my_likes(youtube)
    return render_template('partials/my_likes.html', likes=likes)

@app.route('/delete_selected_saved', methods=['POST'])
def delete_selected_saved():
    playlist_ids = request.form.getlist('playlist_ids')
    saved = [p for p in list_my_saved(build_youtube_api()) if p['id'] not in playlist_ids]
    return render_template('partials/my_saved.html', saved=saved)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
