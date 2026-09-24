"""Single place that knows how to reach the database.
Reads .env so no password is ever hard-coded or committed."""
import os
from dotenv import load_dotenv

load_dotenv()

PGHOST     = os.getenv("PGHOST", "localhost")
PGPORT     = os.getenv("PGPORT", "5432")
PGDATABASE = os.getenv("PGDATABASE", "shortlet")
PGUSER     = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD", "")

def connect():
    """psycopg2 connection, used by the bulk loader."""
    import psycopg2
    return psycopg2.connect(host=PGHOST, port=PGPORT, dbname=PGDATABASE,
                            user=PGUSER, password=PGPASSWORD)

def engine():
    """SQLAlchemy engine, used by pandas.read_sql."""
    from sqlalchemy import create_engine
    from urllib.parse import quote_plus
    pw = quote_plus(PGPASSWORD)
    if PGHOST.startswith("/"):          # Unix socket (Linux/macOS); rare on Windows
        return create_engine(
            f"postgresql+psycopg2://{PGUSER}:{pw}@/{PGDATABASE}"
            f"?host={PGHOST}&port={PGPORT}")
    return create_engine(
        f"postgresql+psycopg2://{PGUSER}:{pw}@{PGHOST}:{PGPORT}/{PGDATABASE}")
