import os

SECRET_KEY=os.getenv('ALTC_SECRET_KEY')
SQLALCHEMY_DATABASE_URI=os.getenv('ALTC_DATABASE_URL')
SENDGRID_API_KEY=os.getenv('SENDGRID_API_KEY')
SECURITY_PASSWORD_SALT=os.getenv('SECURITY_PASSWORD_SALT')
MYSERVER_NAME_SHORT="altCensored"
MYSERVER_NAME="altCensored.com"
MYSERVER_URL="https://altCensored.com"
MYSERVER_TEST_URL="https://altCensored.com"
IARCHIVEURL="https://archive.org/download/youtube-"
IPROXY=os.getenv('IPROXY')
IPROXYBIG=os.getenv('IPROXYBIG')
IPROXYTW=os.getenv('IPROXYTW')
IPROXYTWBIG=os.getenv('IPROXYTWBIG')

SUPPORTED_LANGUAGES = {'en': 'English', 'de': 'Deutsch', 'es': 'Español', 'fr': 'Français', 'pt': 'Portuguese', 'nl': 'Nederlandse', 'it': 'Italiano', 'se': 'Sverige'}
SUPPORTED_THEMES = {'light', 'dark'}
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'UTC'

UPLOAD_FOLDER = '/path/to/the/uploads'


