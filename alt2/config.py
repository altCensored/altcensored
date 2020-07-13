import os

SECRET_KEY=os.getenv('ALTC_SECRET_KEY')
SQLALCHEMY_DATABASE_URI=os.getenv('ALTC_DATABASE_URL')
MYSERVER_NAME_SHORT="altCensored"
MYSERVER_NAME="altCensored.com"
MYSERVER_URL="https://www.altCensored.com"
IARCHIVEURL="https://archive.org/download/youtube-"
IPROXY="https://altcensored.com/ip/180x100/"
IPROXYBIG="https://altcensored.com/ip/320x180/"
IPROXYTW="https://altcensored.com/ip/144x144/"
IPROXYTWBIG="https://altcensored.com/ip/"

SUPPORTED_LANGUAGES = {'en': 'English', 'de': 'Deutsch', 'es': 'Español', 'fr': 'Français', 'pt': 'Portuguese'}
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'UTC'
