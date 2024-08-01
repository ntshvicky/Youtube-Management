from flask import redirect, url_for, session, request, render_template, flash
from werkzeug.utils import secure_filename
import google.oauth2.credentials
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload
from app import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, SCOPES, app, oauth
from app.utils import allowed_file 
from app.youtube_utils import build_youtube_api, list_my_videos, list_my_comments, list_my_likes, list_my_saved, upload_to_youtube, delete_comment, unlike_video

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
    likes = list_my_likes(youtube)
    return render_template('partials/my_likes.html', likes=likes)

@app.route('/delete_selected_saved', methods=['POST'])
def delete_selected_saved():
    playlist_ids = request.form.getlist('playlist_ids')
    saved = [p for p in list_my_saved(build_youtube_api()) if p['id'] not in playlist_ids]
    return render_template('partials/my_saved.html', saved=saved)
