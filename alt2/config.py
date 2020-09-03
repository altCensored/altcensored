import os

SECRET_KEY=os.getenv('ALTC_SECRET_KEY')
SQLALCHEMY_DATABASE_URI=os.getenv('ALTC_DATABASE_URL')
SENDGRID_API_KEY=os.getenv('SENDGRID_API_KEY')
SECURITY_PASSWORD_SALT=os.getenv('SECURITY_PASSWORD_SALT')
MYSERVER_NAME_SHORT="altCensored"
MYSERVER_NAME="altCensored.com"
MYSERVER_URL="https://www.altCensored.com"
IARCHIVEURL="https://archive.org/download/youtube-"
IPROXY="https://altcensored.com/ip/180x100/"
IPROXYBIG="https://altcensored.com/ip/320x180/"
IPROXYTW="https://altcensored.com/ip/144x144/"
IPROXYTWBIG="https://altcensored.com/ip/"

SUPPORTED_LANGUAGES = {'en': 'English', 'de': 'Deutsch', 'es': 'Español', 'fr': 'Français', 'pt': 'Portuguese', 'nl': 'Nederlandse', 'it': 'Italiano', 'se': 'Sverige'}
SUPPORTED_NAVTABS = {'navtab1': 'video', 'navtab2': 'channel', 'navtab3': 'category', 'navtab4': 'playlist', 'navtab5': 'history', 'navtab6': 'settings'}
DEFAULT_NAVTABS = {'tab1': 'video', 'tab2': 'channel', 'tab3': 'category'}
DEFAULT_NAVTAB1 = {'tab1': 'video'}
SUPPORTED_THEMES = {'light', 'dark'}
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'UTC'
