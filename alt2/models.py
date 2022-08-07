from sqlalchemy import Column, Integer, String, DateTime, Boolean, Interval, ARRAY, ForeignKey, BigInteger, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property


from alt2.database import Base

class Entity(Base):
    __tablename__ = 'entity'
    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(String, nullable=False)
    prev = Column(DateTime, nullable=True)
    extractor_key = Column(String, nullable=False)
    extractor_data = Column(String, nullable=False)
    allow = Column(Boolean, nullable=False, default=True)
    title = Column(String, nullable=True)
    views = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    dislikes = Column(Integer, nullable=True)
    yt_comments = Column(Integer, nullable=True)
    yt_views = Column(Integer, nullable=True)
    yt_dislikes = Column(Integer, nullable=True)
    yt_likes = Column(Integer, nullable=True)
    published = Column(DateTime, nullable=True)
    description = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    category = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)
    thumbnail = Column(String, nullable=True)
    alt_url1 = Column(String, nullable=True)
    alt_url2 = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    sync_ia = Column(Boolean, nullable=True)
    exists_ia = Column(Boolean, nullable=True)
    yt_deleted = Column(Boolean, nullable=True)
    sync_iadate = Column(DateTime, nullable=True)
    addeddate = Column(DateTime, nullable=False)    

    def __init__(self, type=None, prev=None):
        self.id = id
        self.type = type
        self.prev = prev
        self.extractor_key = extractor_key
        self.extractor_data = extractor_data
        self.allow = allow
        self.title = title
        self.views = views
        self.likes = likes
        self.dislikes = dislikes
        self.yt_comments = yt_comments
        self.yt_views = yt_views
        self.yt_dislikes = yt_dislikes
        self.yt_likes = yt_likes
        self.published = published
        self.description = description
        self.tags = tags
        self.category = category
        self.rating = rating
        self.thumbnail = thumbnail
        self.alt_url1 = alt_url1
        self.alt_url2 = alt_url2
        self.duration = duration
        self.sync_ia = sync_ia
        self.exists_ia = exists_ia
        self.yt_deleted = yt_deleted
        self.sync_iadate = sync_iadate
        self.addeddate = addeddate

    def __repr__(self):
        return '<Entity %r>' % (self.id)

class Source(Base):
    __tablename__ = 'source'
    id = Column(Integer, primary_key=True, nullable=False)
    next = Column(String, nullable=True)
    delta = Column(Interval, nullable=False)
    url = Column(String, nullable=False)
    extractor_match = Column(String, nullable=False)
    source_name = Column(String, nullable=True)
    ytc_etag = Column(String, nullable=True)
    ytc_id = Column(String, nullable=True)
    ytc_title = Column(String, nullable=True)
    ytc_description = Column(String, nullable=True)
    ytc_customurl = Column(String, nullable=True)
    ytc_publishedat = Column(DateTime, nullable=True)
    ytc_thumbnailurl = Column(String, nullable=True)
    ytc_viewcount = Column(Integer, nullable=True)
    ytc_subscribercount = Column(Integer, nullable=True)
    ytc_videocount = Column(Integer, nullable=True)
    ytc_archive = Column(Boolean, nullable=False, default=False)
    ytc_deleted = Column(String, nullable=True)
    ytc_deleteddate = Column(DateTime, nullable=True)
    ytc_addeddate = Column(DateTime, nullable=True)
    ytc_partarchive = Column(Boolean, nullable=False, default=False)

    def __init__(self, next=None, delta=None):
        self.id = id
        self.next = next
        self.delta = delta
        self.url = url
        self.extractor_match = extractor_match
        self.source_name = source_name
        self.ytc_etag   = ytc_etag
        self.ytc_id = ytc_id
        self.ytc_title = ytc_title
        self.ytc_description = ytc_description
        self.ytc_customurl = ytc_customurl
        self.ytc_publishedat = ytc_publishedat
        self.ytc_thumbnailurl = ytc_thumbnailurl
        self.ytc_viewcount = ytc_viewcount
        self.ytc_subscribercount = ytc_subscribercount
        self.ytc_videocount = ytc_videocount
        self.ytc_archive = ytc_archive
        self.ytc_deleted = ytc_deleted
        self.ytc_deleteddate = ytc_deleteddate
        self.ytc_addeddate = ytc_addeddate
        self.ytc_partarchive = ytc_partarchive

    def __repr__(self):
        return '<Source %r>' % (self.id)


Sources_to_Videos = Table(
    'content', Base.metadata,
    Column('source_id', Integer, ForeignKey('source.id')),
    Column('video_id', Integer, ForeignKey('entity.id')),
)


class Mv_Video(Base):
    __tablename__ = 'mv_video'
    id = Column(Integer, nullable=False, unique=True)
    extractor_data = Column(String, primary_key=True, nullable=False)
    rating = Column(Integer, nullable=True)
    published = Column(DateTime, nullable=True)
    title = Column(String, nullable=True)
    thumbnail = Column(String, nullable=True)
    yt_views = Column(Integer, nullable=True)
    duration = Column(String, nullable=True)
    ytc_title = Column(String, nullable=True)
    ytc_id = Column(String, nullable=True)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    document = Column(String, nullable=True)


    def __init__(self, extractor_data=None, allow=None):
        self.id = id
        self.extractor_data = extractor_data
        self.rating = rating
        self.published = published
        self.title = title
        self.thumbnail = thumbnail
        self.yt_views = yt_views
        self.duration = duration
        self.ytc_title = ytc_title
        self.ytc_id = ytc_id
        self.description = description
        self.category = category
        self.tags = tags
        self.document = document
  
    def __repr__(self):
        return '<Mv_Video %r>' % (self.id)


class Mv_Channel(Base):
    __tablename__ = 'mv_channel'
    id = Column(Integer, unique=True, nullable=False)
    ytc_id = Column(String, primary_key=True, nullable=False)
    ytc_title = Column(String, nullable=True)
    ytc_publishedat = Column(DateTime, nullable=True)
    ytc_thumbnailurl = Column(String, nullable=True)
    ytc_viewcount = Column(Integer, nullable=True)
    ytc_subscribercount = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)
    limited = Column(Integer, nullable=True)
    ytc_description = Column(String, nullable=True)
    ytc_deleted = Column(String, nullable=True)
    ytc_archive = Column(String, nullable=True)
    allow = Column(String, nullable=True)
    delta = Column(DateTime, nullable=True)
    ytc_deleteddate = Column(DateTime, nullable=True)
    ytc_addeddate = Column(DateTime, nullable=True)
    ytc_partarchive = Column(Boolean, nullable=False, default=False)


    def __init__(self, ytc_id=None, ytc_title=None):
        self.id = id
        self.ytc_id = ytc_id        
        self.ytc_title = ytc_title
        self.ytc_publishedat = ytc_publishedat
        self.ytc_thumbnailurl = ytc_thumbnailurl
        self.ytc_viewcount = ytc_viewcount
        self.ytc_subscribercount = ytc_subscribercount
        self.total = total       
        self.limited = limited
        self.ytc_description = ytc_description
        self.ytc_deleted = ytc_deleted
        self.ytc_archive = ytc_archive
        self.allow = allow
        self.ytc_deleteddate = ytc_deleteddate        
        self.ytc_addeddate = ytc_addeddate
        self.ytc_partarchive = ytc_partarchive
        self.delta = delta

    def __repr__(self):
        return '<Mv_Channel %r>' % (self.ytc_id)

    @hybrid_property
    def archive(self):
        return self.ytc_archive | self.ytc_partarchive


class Category(Base):
    __tablename__ = 'category'
    cat_id = Column(Integer, primary_key=True, unique=True, nullable=False)
    cat_name = Column(String, unique=True, nullable=False)
    cat_image  = Column(String, nullable=False)

    def __init__(self, next=None, delta=None):
        self.cat_id = cat_id
        self.cat_name = cat_name
        self.cat_image = cat_image

    def __repr__(self):
        return '<Category %r>' % (self.cat_id)


class Mv_Category(Base):
    __tablename__ = 'mv_category'
    cat_id = Column(Integer, primary_key=True, unique=True, nullable=False)
    cat_name = Column(String, unique=True, nullable=False)
    cat_image  = Column(String, nullable=False)
    cat_count = Column(Integer, nullable=False)

    def __init__(self, next=None, delta=None):
        self.cat_id = cat_id
        self.cat_name = cat_name
        self.cat_image = cat_image
        self.cat_count = cat_count

    def __repr__(self):
        return '<Mv_Category %r>' % (self.cat_id)


class Language(Base):
    __tablename__ = 'language'
    lang_id = Column(Integer, primary_key=True, unique=True, nullable=False)
    lang_name = Column(String, unique=True, nullable=False)
    lang_image  = Column(String, nullable=False)
    lang_tagstring  = Column(String, nullable=False)
    lang_code  = Column(String, nullable=False)
    lang_image_css  = Column(String, nullable=False)

    def __init__(self, next=None, delta=None):
        self.lang_id = lang_id
        self.lang_name = lang_name
        self.lang_image = lang_image
        self.lang_tagstring = lang_tagstring
        self.lang_code = lang_code        
        self.lang_image_css = lang_image_css


class User(Base):
    __tablename__ = 'altcen_user'
    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False)
    email_verified = Column(Boolean, nullable=False, default=False)
    email_subscribed = Column(Boolean, nullable=False, default=True)
    email_action = Column(String, nullable=True)
    password = Column(String, nullable=False)
    watched = Column(ARRAY(String))
    watchlater = Column(ARRAY(String))
    created_date = Column(DateTime, nullable=True)
    email_verified_date = Column(DateTime, nullable=True)
    email_lastsent_date = Column(DateTime, nullable=True)
    updated = Column(DateTime, nullable=True)
    navtabs = Column(ARRAY(String))
    navtabs_index = Column(ARRAY(String))
    username = Column(String, nullable=True)
    description = Column(String, nullable=True)
    public = Column(Boolean, nullable=False, default=False)
    view_counter = Column(Integer, nullable=True)
    settings = Column(MutableDict.as_mutable(JSON))
    featured_playlist = Column(MutableDict.as_mutable(JSON))
#    playlists = relationship("Playlist", cascade="all, delete-orphan")
    playlists = relationship("Playlist", cascade="all, delete-orphan", back_populates="user")



class Mv_Altcen_user(Base):
    __tablename__ = 'mv_altcen_user'
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=True)
    description = Column(String, nullable=True)
    public = Column(Boolean, nullable=False, default=False)
    view_counter = Column(Integer, nullable=True)
    featured_playlist = Column(MutableDict.as_mutable(JSON))

    def __init__(self, next=None, delta=None):
        self.id = id
        self.username = username
        self.description = description

    def __repr__(self):
        return '<Mv_Altcen_user %r>' % (self.id)

class Playlist(Base):
    __tablename__ = 'playlist'
    id = Column(Integer, primary_key=True, nullable=False)
    hashid = Column(String, nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    videos = Column(ARRAY(String))
    video_count = Column(Integer, nullable=True)
    created = Column(DateTime, nullable=True)
    updated = Column(DateTime, nullable=True)
    public = Column(Boolean, nullable=False, default=True)
    view_counter = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey('altcen_user.id'), nullable=False)
    featured_video =  Column(MutableDict.as_mutable(JSON))
#    user = relationship("User", backref="playlist")
    user = relationship("User", back_populates="playlists")



class Mv_Playlist(Base):
    __tablename__ = 'mv_playlist'
    id = Column(Integer, primary_key=True, nullable=False)
    hashid = Column(String, nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    videos = Column(ARRAY(Integer))
    video_count = Column(Integer, nullable=True)
    created = Column(DateTime, nullable=True)
    updated = Column(DateTime, nullable=True)
    public = Column(Boolean, nullable=False, default=True)
    view_counter = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey('altcen_user.id'), nullable=False)
    featured_video =  Column(MutableDict.as_mutable(JSON))
    user = relationship("User", backref="mv_playlist")


    def __init__(self, next=None, delta=None):
        self.id = id
        self.hashid = hashid
        self.title = title
        self.description = description

    def __repr__(self):
        return '<Mv_Playlist %r>' % (self.id)

class Translation(Base):
    __tablename__ = 'translation'
    varname = Column(String, primary_key=True, nullable=False)
    en = Column(String, nullable=False)
    de = Column(String, nullable=True)
    es = Column(String, nullable=True)
    fr = Column(String, nullable=True)
    pt = Column(String, nullable=True)
    nl = Column(String, nullable=True)
    it = Column(String, nullable=True)
    se = Column(String, nullable=True)


class Counter(Base):
    __tablename__ = 'counter'
    hash = Column(BigInteger, primary_key=True, nullable=False)


class Email_list(Base):
    __tablename__ = 'email_list'
    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False)
    username = Column(String, nullable=True)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    email_source = Column(String, nullable=False)
    email_subscribed = Column(Boolean, nullable=False, default=True)
    email_action = Column(String, nullable=True)
    created_date = Column(DateTime, nullable=True)
    email_lastsent_date = Column(DateTime, nullable=True)
    updated = Column(DateTime, nullable=True)


class Channels(Base):
    __tablename__ = 'channels'
    url = Column(String, primary_key=True, nullable=False)
    synched = Column(Boolean, nullable=True)
    working = Column(Boolean, nullable=True)
    syncdate = Column(DateTime, nullable=True)


class Channels_part(Base):
    __tablename__ = 'channels_part'
    ytc_id = Column(String, primary_key=True, nullable=False)
    synched = Column(Boolean, nullable=True)
    working = Column(Boolean, nullable=True)
    syncdate = Column(DateTime, nullable=True)
