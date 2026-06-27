from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from ytac.db import Base, MvBase
from gevent import getcurrent
from . import config

dbase = config.SQLALCHEMY_DATABASE_URI

engine = create_engine(dbase,
                       pool_size=3,
                       max_overflow=9,
#                       echo=True,
#                       echo_pool="debug",
#                       pool_use_lifo=True,
                       pool_pre_ping=True,
                       pool_recycle=1800,
                       pool_timeout=10,
                       connect_args={"connect_timeout": 5},
                       )

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine),
                            scopefunc=getcurrent)
Base.query = db_session.query_property()
MvBase.query = db_session.query_property()


def init_db(app):
    from alt2 import models
    Base.metadata.create_all(bind=engine)
