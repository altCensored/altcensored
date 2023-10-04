from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from . import config

dbase = config.SQLALCHEMY_DATABASE_URI

engine = create_engine(dbase,
                       pool_size=5,
                       max_overflow=25,
#                       echo=True,
#                       echo_pool="debug",
#                       pool_use_lifo=True,
                       pool_pre_ping=True
                       )

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db(app):
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import models
    Base.metadata.create_all(bind=engine)