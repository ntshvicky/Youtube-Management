# Youtube Management

pip install Flask Flask-OAuthlib google-api-python-client google-auth-httplib2 google-auth-oauthlib

pip install Flask Authlib google-api-python-client google-auth-httplib2 google-auth-oauthlib


pip install python-dotenv

git rm -r --cached env/

find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf  


##### setup ####
set in https://console.cloud.google.com/ -> credentials

1. Authorised JavaScript origins 

http://localhost

http://localhost:5000



2. Authorised redirect URIs
http://localhost:5000/authorized

https://ytmanage.nitishsrivastava.com/