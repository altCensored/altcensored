import logging
import os
from http.client import HTTPSConnection
from urllib.parse import urlparse

from flask import current_app
from internetarchive import get_item
from sqlalchemy.orm.attributes import flag_modified

from ..cache import cache
from ..database import db_session
from ..models import Entity

logger = logging.getLogger(__name__)


def get_video_files(item):
    extensions = ['webm', 'mp4', 'ogv', 'mkv']
    video_files = []
    for ext in extensions:
        for file in item.get_files(glob_pattern=f"*.{ext}"):
            video_files.append(file)
        if video_files:
            break
    return video_files


def check_video_files(ia_item):
    files_list = ia_item.item_metadata.get('files', [])
    extensions = ['.webm', '.mp4', '.ogv', '.mkv']
    filename = None
    for x in files_list:
        if x['source'] == 'original' and any(ext in x['name'] for ext in extensions):
            filename = x.get("name")
    return filename


def get_video_files_2(ia_item):
    files_list = ia_item.item_metadata.get('files', [])
    extensions = ['.webm', '.mp4', '.ogv', '.mkv']
    videofile_full = None
    for x in files_list:
        if x['source'] == 'original' and any(ext in x['name'] for ext in extensions):
            videofile_full = x.get("name")
    return videofile_full


def get_image_file(ia_item):
    files_list = ia_item.item_metadata.get('files', [])
    image_extensions = ('.jpg', '.webp', '.png')
    allowed_formats = {'JPEG', 'WebP', 'PNG'}

    video_id = ia_item.identifier.replace('youtube-', '', 1)
    for ext in image_extensions:
        for x in files_list:
            if x['name'] == video_id + ext:
                return x['name']

    for x in files_list:
        if (x['source'] == 'original'
                and x.get('format') in allowed_formats
                and x['name'].endswith(image_extensions)):
            return x['name']

    for x in files_list:
        if x['name'] == '__ia_thumb.jpg':
            return x['name']

    return None


def ac_object_exist(client, s3_bucket, itemname: str) -> bool:
    objects = client.list_objects(s3_bucket, prefix=itemname)
    return any(True for _ in objects)


@cache.memoize(timeout=3600)
def check_ac_object_exists(video_id: str) -> bool:
    client = current_app.minio_client
    if client is None:
        return False
    return ac_object_exist(client, current_app.config['AC_S3_BUCKET'], video_id)


def get_ia_item(extractor_data):
    IARCHIVEURL = current_app.config['IARCHIVEURL']
    VIDEOSERVER_URL = current_app.config['VIDEOSERVER_URL']
    ia_item = get_item('youtube-' + extractor_data)
    entity_video = Entity.query.filter(Entity.extractor_data == extractor_data).scalar()
    if len(ia_item.item_metadata) != 0:
        videofile_full = get_video_files_2(ia_item)
        thumbnail_full = get_image_file(ia_item)
        if thumbnail_full:
            entity_video.thumbnail = thumbnail_full
        if videofile_full:
            root, ext = os.path.splitext(videofile_full)
            entity_video.videofile = root
            flag_modified(entity_video, "thumbnail")
            flag_modified(entity_video, "videofile")
            db_session.commit()
            return IARCHIVEURL + extractor_data + "/" + root
        else:
            entity_video.novideo_ia = True
            flag_modified(entity_video, "novideo_ia")
            db_session.commit()
            return f'{VIDEOSERVER_URL}unavailable/unavailable'
    else:
        return f'{VIDEOSERVER_URL}unavailable/unavailable'


def site_is_online(url, timeout=1):
    parser = urlparse(url)
    host = parser.netloc or parser.path.split("/")[0]
    for port in (80, 443):
        connection = HTTPSConnection(host=host, port=port, timeout=timeout)
        try:
            connection.request("HEAD", "/")
            return True
        except Exception:
            pass
        finally:
            connection.close()
    return False
