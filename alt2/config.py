import os

SECRET_KEY=os.getenv('ALTC_SECRET_KEY')
SQLALCHEMY_DATABASE_URI=os.getenv('ALTC_DATABASE_URL')
SENDGRID_API_KEY=os.getenv('SENDGRID_API_KEY')
SECURITY_PASSWORD_SALT=os.getenv('SECURITY_PASSWORD_SALT')
MYSERVER_NAME_SHORT="altCensored"
MYSERVER_NAME="altCensored.com"
MYSERVER_URL="https://altCensored.com"
MYSERVER_TEST_URL="http://127.0.0.1:5000"
VIDEO_THUMB_ERROR_IMAGE="https://altCensored.com/image_error.webp"
CHANNEL_THUMB_ERROR_IMAGE="https://altCensored.com/channel_unnamed.jpg"

IARCHIVEURL="https://archive.org/download/youtube-"
IARCHIVEITEMURL="https://archive.org/details/youtube-"
IARCHIVEMETAURL="archive.org/metadata/youtube-"

IARCHIVEITEMFS=os.getenv('IARCHIVEITEMFS')

VIDEOSERVER_URL=os.getenv('VIDEOSERVER_URL')
#VIDEOSERVER_URL="https://videos.altCensored.com"
#VIDEOSERVER_URL="https://s3.altCensored.com/videos"
#IMAGESERVER_URL=os.getenv('IMAGESERVER_URL')

IPROXY=os.getenv('IPROXY')
IPROXYBIG=os.getenv('IPROXYBIG')
IPROXYHUGE=os.getenv('IPROXYHUGE')
IPROXYTW=os.getenv('IPROXYTW')
IPROXYTWBIG=os.getenv('IPROXYTWBIG')
PROPAGATE_EXCEPTIONS=False

ACIPROXYHUGE=os.getenv('ACIPROXYHUGE')
ACIPROXY=os.getenv('ACIPROXY')

SUPPORTED_LANGUAGES = {'en': 'English', 'de': 'Deutsch', 'es': 'Español', 'fr': 'Français', 'pt': 'Portuguese', 'nl': 'Nederlandse', 'it': 'Italiano', 'se': 'Sverige'}
SUPPORTED_THEMES = {'light', 'dark'}
DEFAULT_THEME = 'light'
DEFAULT_PLAYNEXT = 'True'
DEFAULT_LOOPLIST = 'True'
DEFAULT_AUTOPLAY = 'True'

BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'UTC'

UPLOAD_FOLDER = '/templates/newsletter'
SES_REGION_NAME=os.getenv('SES_REGION_NAME') or 'us-east-1'
SES_EMAIL_SOURCE=os.getenv('SES_EMAIL_SOURCE') or 'newsletter@altcensored.com'
SES_EMAIL_SOURCE_WELCOME=os.getenv('SES_EMAIL_SOURCE_WELCOME') or 'registration@altcensored.com'
AWS_ACCESS_KEY_ID=os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY=os.getenv('AWS_SECRET_ACCESS_KEY')

MJ_API_KEY = os.getenv('MJ_APIKEY_PUBLIC')
MJ_API_SECRET = os.getenv('MJ_APIKEY_PRIVATE')

VPN_API_AUTH = os.getenv('VPN_API_AUTH')
VPN_API_PORT = '8445'
VPN_PORT = '51820'

VPN_FREE_BWLIMIT = 5120
VPN_DEFAULT_BWLIMIT = 0
VPN_DEFAULT_SUBEXPIRY = '2023-Oct-28 12:39:05 PM'
VPN_DEFAULT_IPINDEX = 0
VPN_FOLDER = 'templates/vpn'

CACHE_TYPE = 'RedisCache'
CACHE_DEFAULT_TIMEOUT = 3600
CACHE_REDIS_HOST=os.getenv('CACHE_REDIS_HOST')
CACHE_REDIS_DB=1

REV_ID = os.getenv('REV_ID')

SENTRY_DSN = os.getenv('SENTRY_DSN')

AC_S3_ENDPOINT=os.getenv('AC_S3_ENDPOINT')
AC_S3_BUCKET=os.getenv('AC_S3_BUCKET')
AC_S3_ACCESS_KEY=os.getenv('AC_S3_ACCESS_KEY')
AC_S3_SECRET_KEY=os.getenv('AC_S3_SECRET_KEY')

RANDOM_VALUE=os.getenv('RANDOM_VALUE')

#FLASH_MSG = 'Download preferred videos, Internet Archive is <a href=https://archive.org/details/youtube-Gv4jjFgIP_g class="alert-link" target="_blank" rel="noopener noreferrer" span style="color: darkorange;">limiting access on some items</a>'
#FLASH_MSG  = "Download preferred videos, Internet Archive is limiting access"
FLASH_MSG = None
#FLASH_MSG = '<a href=https://altcensored.com/donate class="alert-link" target="_blank" rel="noopener noreferrer" span style="color: darkorange;">We Need Your Help</a>'

