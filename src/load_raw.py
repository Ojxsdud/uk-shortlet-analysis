"""Load Inside Airbnb CSVs into staging. Builds staging tables from each file's
actual header, so a snapshot that adds or drops columns still loads."""
import gzip, csv, os, sys
from db import connect

CITIES = ["london", "edinburgh", "manchester"]
KINDS  = ["listings", "calendar", "reviews"]
RAW    = "data/raw"

def header_of(path):
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as f:
        return next(csv.reader(f))

def quote(c):
    return '"' + c.replace('"', '""') + '"'

def load(conn, city, kind):
    path = f"{RAW}/{city}_{kind}.csv.gz"
    if not os.path.exists(path):
        print(f"  skip (missing): {path}"); return 0
    cols = header_of(path)
    tbl  = f"staging.{kind}"
    cur  = conn.cursor()

    cur.execute(f"SELECT to_regclass('{tbl}')")
    if cur.fetchone()[0] is None:
        ddl = ", ".join(f"{quote(c)} text" for c in cols)
        cur.execute(f"CREATE TABLE {tbl} ({ddl}, city text)")
        print(f"  created {tbl} with {len(cols)} columns")
    else:
        cur.execute("""SELECT column_name FROM information_schema.columns
                       WHERE table_schema='staging' AND table_name=%s
                         AND column_name<>'city' ORDER BY ordinal_position""", (kind,))
        existing = [r[0] for r in cur.fetchall()]
        for c in cols:
            if c not in existing:
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {quote(c)} text")
                print(f"  + new column in {city}: {c}")

    collist = ", ".join(quote(c) for c in cols)
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as f:
        cur.copy_expert(
            f"""COPY {tbl} ({collist}) FROM STDIN
                WITH (FORMAT csv, HEADER true, QUOTE '"', ESCAPE '"')""", f)
    n = cur.rowcount
    cur.execute(f"UPDATE {tbl} SET city=%s WHERE city IS NULL", (city,))
    conn.commit()
    print(f"  {city}/{kind}: {n:,} rows")
    return n

def main():
    conn = connect()
    total = 0
    for city in CITIES:
        print(city)
        for kind in KINDS:
            total += load(conn, city, kind)
    print(f"TOTAL {total:,} rows")

if __name__ == "__main__":
    main()
