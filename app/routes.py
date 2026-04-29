import os
from functools import wraps

from authlib.integrations.base_client import OAuthError
from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from app import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, SCOPES, app, oauth
from app.utils import allowed_file
from app.youtube_utils import build_youtube_api, clear_video_rating, delete_comment, delete_playlist, delete_video, get_my_channel, list_comments_on_my_videos, list_my_comments, list_my_dislikes, list_my_likes, list_my_playlists, list_my_videos, upload_to_youtube


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'google_token' not in session:
            flash('Please sign in with Google first.')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped


def oauth_configured():
    return bool(OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET and 'your-google-oauth' not in OAUTH_CLIENT_ID)


@app.route('/')
def index():
    if 'google_token' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login')
def login():
    if not oauth_configured():
        flash('Google OAuth is not configured yet. Add OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET in Vercel environment variables.')
        return redirect(url_for('index'))
    return oauth.google.authorize_redirect(url_for('authorized', _external=True), access_type='offline', prompt='consent')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/authorized')
def authorized():
    try:
        token = oauth.google.authorize_access_token()
    except OAuthError as error:
        flash(f'Google login failed: {error.error}. Check OAuth credentials and redirect URI.')
        return redirect(url_for('index'))
    session['google_token'] = {'token': token['access_token'], 'refresh_token': token.get('refresh_token'), 'token_uri': 'https://oauth2.googleapis.com/token', 'client_id': OAUTH_CLIENT_ID, 'client_secret': OAUTH_CLIENT_SECRET, 'scopes': SCOPES}
    youtube = build_youtube_api()
    session['youtube_channel'] = get_my_channel(youtube)
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('base.html', channel=session.get('youtube_channel'))


@app.route('/my_videos')
@login_required
def my_videos():
    return render_template('partials/my_videos.html', videos=list_my_videos(build_youtube_api()))


@app.route('/my_comments')
@login_required
def my_comments():
    return render_template('partials/my_comments.html', comments=list_my_comments(build_youtube_api()), heading='Comments I Made On My Channel')


@app.route('/video_comments')
@login_required
def video_comments():
    return render_template('partials/my_comments.html', comments=list_comments_on_my_videos(build_youtube_api()), heading='Comments On My Videos')


@app.route('/my_comment_history')
@login_required
def my_comment_history():
    return render_template('partials/my_comment_history.html')


@app.route('/my_likes')
@login_required
def my_likes():
    return render_template('partials/my_likes.html', videos=list_my_likes(build_youtube_api()), rating_name='likes')


@app.route('/my_dislikes')
@login_required
def my_dislikes():
    return render_template('partials/my_likes.html', videos=list_my_dislikes(build_youtube_api()), rating_name='dislikes')


@app.route('/my_playlists')
@login_required
def my_playlists():
    return render_template('partials/my_saved.html', playlists=list_my_playlists(build_youtube_api()))


@app.route('/view_history')
@login_required
def view_history():
    return render_template('partials/view_history.html')


@app.route('/upload_video', methods=['GET', 'POST'])
@login_required
def upload_video():
    if request.method == 'POST':
        file = request.files.get('video_file')
        if not file or file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('Unsupported video type')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        upload_to_youtube(build_youtube_api(), request.form['title'], request.form['description'], filepath, request.form.get('privacy_status', 'private'), request.form.get('tags', ''), request.form.get('category_id', '22'), request.form.get('made_for_kids') == 'true')
        flash('Video successfully uploaded to YouTube')
        return redirect(url_for('dashboard'))
    return render_template('upload_video.html', channel=session.get('youtube_channel'))


@app.route('/delete_selected_comments', methods=['POST'])
@login_required
def delete_selected_comments():
    youtube = build_youtube_api()
    for comment_id in request.form.getlist('comment_ids'):
        delete_comment(youtube, comment_id)
    return my_comments()


@app.route('/delete_selected_videos', methods=['POST'])
@login_required
def delete_selected_videos():
    youtube = build_youtube_api()
    for video_id in request.form.getlist('video_ids'):
        delete_video(youtube, video_id)
    return my_videos()


@app.route('/clear_selected_ratings/<rating_name>', methods=['POST'])
@login_required
def clear_selected_ratings(rating_name):
    youtube = build_youtube_api()
    for video_id in request.form.getlist('video_ids'):
        clear_video_rating(youtube, video_id)
    return my_dislikes() if rating_name == 'dislikes' else my_likes()


@app.route('/delete_selected_playlists', methods=['POST'])
@login_required
def delete_selected_playlists():
    youtube = build_youtube_api()
    for playlist_id in request.form.getlist('playlist_ids'):
        delete_playlist(youtube, playlist_id)
    return my_playlists()
