from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from config.settings import settings

Base = declarative_base()
engine = create_engine(
    settings.neon_connection_string,
    pool_pre_ping=True,       # test connections before use (detects dead Neon connections)
    pool_recycle=300,          # recycle connections every 5 min (Neon closes idle ones)
    pool_size=5,               # keep 5 connections in pool
    max_overflow=10,           # allow up to 10 extra connections under load
    connect_args={
        "connect_timeout": 10,
        # NOTE: Neon pooler rejects statement_timeout as a startup param.
        # We set it via an event listener below instead.
    },
)

# Set statement_timeout after connection is established (Neon pooler compatible)
@event.listens_for(engine, "connect")
def _set_statement_timeout(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET statement_timeout = '30s'")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
