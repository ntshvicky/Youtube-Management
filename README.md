# YouTube Management

A Flask web app for managing a signed-in user's YouTube account with Google OAuth and the official YouTube Data API v3.

The app is built for any YouTube user, not just one fixed account. Users can sign in with Google, grant YouTube permissions, and manage the resources that YouTube's API allows for their account.

![Login screen](screenshots/login-screen.jpg)

## Features

- Google OAuth login for YouTube users
- Creator dashboard with left-side navigation
- View uploaded videos from the signed-in channel
- Upload new videos with required YouTube metadata
- Delete selected uploaded videos
- View liked videos and remove selected likes
- View disliked videos and remove selected dislikes
- View comments available through the signed-in user's channel/video resources
- Delete selected comments
- View playlists owned by the signed-in account
- Delete selected playlists
- Bulk select actions for supported lists
- Comment History shortcut to Google My Activity for comments made on other users' videos
- Watch history notice explaining YouTube API limitations

## Tech Stack

- Python
- Flask
- Authlib
- Google OAuth
- YouTube Data API v3
- Bootstrap 4
- Bootstrap Icons
- jQuery
- python-dotenv

## Project Structure

```text
.
├── app.py
├── passenger_wsgi.py
├── requirements.txt
├── .env.example
├── screenshots
│   └── login-screen.jpg
└── app
    ├── __init__.py
    ├── routes.py
    ├── utils.py
    ├── youtube_utils.py
    └── templates
        ├── base.html
        ├── index.html
        ├── upload_video.html
        └── partials
            ├── my_comment_history.html
            ├── my_comments.html
            ├── my_likes.html
            ├── my_saved.html
            ├── my_videos.html
            └── view_history.html
```

## Requirements

- Python 3.10 or newer
- A Google Cloud project
- YouTube Data API v3 enabled
- OAuth consent screen configured
- OAuth 2.0 Client ID and Client Secret

## Google Cloud Setup

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable **YouTube Data API v3**.
4. Open **APIs & Services > OAuth consent screen**.
5. Configure the app name, support email, developer contact email, and required scopes.
6. Open **APIs & Services > Credentials**.
7. Create an **OAuth client ID**.
8. Choose **Web application** as the application type.
9. Add your local development URLs.

For local development on port `5000`:

```text
Authorized JavaScript origins:
http://localhost:5000

Authorized redirect URIs:
http://localhost:5000/authorized
```

If port `5000` is busy and you run the app on port `5001`, add:

```text
Authorized JavaScript origins:
http://localhost:5001
http://127.0.0.1:5001

Authorized redirect URIs:
http://localhost:5001/authorized
http://127.0.0.1:5001/authorized
```

For production, add your deployed domain:

```text
Authorized JavaScript origins:
https://your-domain.com

Authorized redirect URIs:
https://your-domain.com/authorized
```

## OAuth Scopes

The app requests these scopes:

```text
openid
email
profile
https://www.googleapis.com/auth/youtube
https://www.googleapis.com/auth/youtube.force-ssl
https://www.googleapis.com/auth/youtube.upload
```

These scopes allow account management actions. Google may require OAuth app verification before the app is available broadly to public users.

## Environment Variables

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Fill in your own Google OAuth credentials:

```env
SECRET_KEY=change-this-secret
OAUTH_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
OAUTH_CLIENT_SECRET=your-google-oauth-client-secret
```

Never commit `.env`. It is intentionally ignored by `.gitignore`.

## Install Locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run Locally

Default port:

```bash
python app.py
```

Open:

```text
http://localhost:5000
```

If port `5000` is already in use:

```bash
. .venv/bin/activate
flask --app app run --debug --host 0.0.0.0 --port 5001
```

Open:

```text
http://localhost:5001
```

Make sure the matching redirect URI is added in Google Cloud.

## Important API Limitations

The public YouTube Data API does not expose every feature available in YouTube's own website.

Current limitations:

- Full watch history is not available through YouTube Data API v3.
- A global API endpoint for every comment a user has posted across other users' videos is not available.
- The app can show comments available through channel/video comment APIs.
- The Comment History menu item links to Google My Activity for cross-YouTube comment history.
- Some delete actions can fail if the signed-in user does not own the resource or lacks moderation permission.
- YouTube API quota limits apply.

## Destructive Actions

Be careful with these actions because they affect the real signed-in YouTube account:

- Delete videos
- Delete playlists
- Delete comments
- Remove likes
- Remove dislikes

Deleted YouTube resources may not be recoverable.

## Common Problems

### Redirect URI mismatch

Google OAuth will fail if the URL running locally does not exactly match the redirect URI in Google Cloud.

For example, these are different:

```text
http://localhost:5001/authorized
http://127.0.0.1:5001/authorized
```

Add whichever one you use in the browser.

### Missing OAuth credentials

If login says OAuth is not configured, create `.env`, add your credentials, and restart Flask.

### OAuth app not verified

If Google shows a warning or blocks users, add test users in Google Cloud or complete OAuth app verification.

### Missing dependencies

Install dependencies inside the virtual environment:

```bash
. .venv/bin/activate
pip install -r requirements.txt
```

## Deployment Notes

For production:

1. Set `SECRET_KEY`, `OAUTH_CLIENT_ID`, and `OAUTH_CLIENT_SECRET` as server environment variables.
2. Use HTTPS.
3. Add the production redirect URI in Google Cloud.
4. Use a production WSGI server instead of Flask's development server.
5. Keep OAuth credentials private.
6. Complete Google OAuth verification if needed.

The repository includes `passenger_wsgi.py` for hosts that support Passenger Python apps.

## Security Notes

- Never commit `.env`.
- Use a strong `SECRET_KEY`.
- Keep OAuth Client Secret private.
- Do not expose OAuth credentials in frontend code.
- Review requested Google API scopes before publishing.
- Treat bulk delete actions carefully.

## Author

Created by [ntshvicky](https://github.com/ntshvicky).
