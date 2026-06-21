from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from urllib.parse import urlsplit, urlunsplit, parse_qs
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///career_copilot.db")

if DATABASE_URL.startswith("sqlite"):
    clean_url = DATABASE_URL
    ssl_mode = None
    ssl_ca = None
else:
    # Strip SSL-related query params that some DBAPI drivers reject.
    parts = urlsplit(DATABASE_URL)
    qs = parse_qs(parts.query)
    ssl_mode = qs.get("ssl_mode", [None])[0]
    ssl_ca = qs.get("ssl_ca", [None])[0]
    clean_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))

# Build connect_args depending on available DBAPI
connect_args = {}
try:
    import pymysql  # type: ignore
    dbapi = "pymysql"
except Exception:
    try:
        import MySQLdb  # type: ignore
        dbapi = "mysqldb"
    except Exception:
        dbapi = None

if ssl_ca:
    # Both pymysql and mysqlclient accept an 'ssl' dict with 'ca'
    connect_args["ssl"] = {"ca": ssl_ca}
elif ssl_mode:
    # If only ssl_mode was provided, don't forward it to the DBAPI; leave SSL off
    # or let the server negotiate. You can handle specific modes here if needed.
    pass

engine = create_engine(clean_url, pool_pre_ping=True, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()




