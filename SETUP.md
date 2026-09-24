# Setup and run guide

Every command and script here was executed end to end against PostgreSQL 16.13 with
synthetic data shaped exactly like Inside Airbnb's real files (75-column listings,
`"$1,250.00"` prices, `"1.5 shared baths"`, `t`/`f` booleans, JSON amenity arrays,
embedded newlines and quotes in text fields). The full pipeline completes with zero
errors and the dashboard renders all five tabs with zero exceptions.

---

## 1. Software to install

| What | Version | Where | Notes |
|---|---|---|---|
| **PostgreSQL** | 16.x | postgresql.org/download/windows | Tick pgAdmin 4 and Command Line Tools in the installer. Set a password you'll remember — it goes in `.env`. |
| **Python** | 3.11 or 3.12 | python.org/downloads | **Tick "Add python.exe to PATH"** on the first installer screen. Not 3.13 — some wheels lag. |
| **Git** | latest | git-scm.com/download/win | Accept the defaults. |
| **VS Code** | latest | code.visualstudio.com | Install the Python and PostgreSQL extensions. |

Nothing else is needed. You do **not** need Docker, WSL, Power BI, or a cloud account.

### Confirm the installs

Open **PowerShell** (not Command Prompt) and run:

```powershell
python --version        # Python 3.11.x or 3.12.x
git --version
psql --version          # psql (PostgreSQL) 16.x
```

If `psql` isn't found, add it to PATH:

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"
```

To make that permanent: Start → "Edit the system environment variables" → Environment
Variables → Path → New → `C:\Program Files\PostgreSQL\16\bin`.

---

## 2. Project setup

```powershell
cd C:\Users\ryuss
mkdir uk-shortlet-analysis
cd uk-shortlet-analysis
```

Unzip the supplied project files into this folder, then:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then install:

```powershell
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

You should see `(venv)` at the start of your prompt. **Everything below assumes the
venv is active.** If you close the terminal, re-run `.\venv\Scripts\Activate.ps1`.

---

## 3. Database

Create the database (you'll be prompted for the password you set at install):

```powershell
psql -U postgres -c "CREATE DATABASE shortlet;"
```

Copy `.env.example` to `.env` and fill in your password:

```
PGHOST=localhost
PGPORT=5432
PGDATABASE=shortlet
PGUSER=postgres
PGPASSWORD=whatever_you_set
```

`.env` is in `.gitignore` and must never be committed. Everything reads the database
connection from this one file via `src/db.py`, so the password appears nowhere else.

---

## 4. Get the data

Go to **insideairbnb.com/get-the-data** in a browser. Don't guess the URLs — the path
contains a snapshot date that changes each quarter.

For each of London, Edinburgh and Manchester, download from the **data** section (not
the "visualisations" section — that `listings.csv` is a cut-down 18-column version):

- `listings.csv.gz`
- `calendar.csv.gz`
- `reviews.csv.gz`
- `neighbourhoods.geojson`

Save them into `data\raw\` renamed with the city as a prefix:

```
data\raw\london_listings.csv.gz
data\raw\london_calendar.csv.gz
data\raw\london_reviews.csv.gz
data\raw\london_neighbourhoods.geojson
data\raw\edinburgh_listings.csv.gz
...
```

**Write down the snapshot date.** It goes in the README, on the dashboard and in the
LinkedIn post.

### Try the pipeline before you download anything

There's a generator that produces correctly-shaped fake data, so you can prove the whole
pipeline works on your machine in under a minute:

```powershell
python src\make_fake_sample_data.py
bash run_all.sh        # or run the steps in section 5 one by one
```

If that works, any later failure is about the real data, not your setup. Delete
`data\raw\*` afterwards and download the real files.

---

## 5. Run it

There's a `run_all.sh` that does everything. On Windows, either use Git Bash
(`bash run_all.sh`) or run the eight steps individually in PowerShell:

```powershell
# 1. Create the schema (drops and recreates - safe to re-run)
psql -U postgres -d shortlet -v ON_ERROR_STOP=1 -f sql\01_schema.sql

# 2. Load the CSVs into staging.  SLOWEST STEP - several minutes on real data,
#    because London's calendar alone is ~35 million rows.
python src\load_raw.py

# 3. Clean and type everything into core
psql -U postgres -d shortlet -v ON_ERROR_STOP=1 -f sql\02_transform.sql

# 4. Create the analysis views
psql -U postgres -d shortlet -v ON_ERROR_STOP=1 -f sql\03_views.sql

# 5. Indexes - AFTER loading, never before
psql -U postgres -d shortlet -v ON_ERROR_STOP=1 -f sql\04_indexes.sql

# 6. The ten analysis queries, each written out as a CSV
Get-ChildItem sql\analysis\q*.sql | ForEach-Object {
    psql -U postgres -d shortlet --csv -f $_.FullName > "outputs\$($_.BaseName).csv"
}

# 7. Train the model and produce the SHAP plots
python src\model.py

# 8. Export the small parquet files the dashboard reads
python src\export_for_app.py

# 9. Launch
streamlit run app\dashboard.py
```

Expected timings on real data (a normal laptop):

| Step | Synthetic (6.5k listings) | Real (~100k listings, 35M calendar rows) |
|---|---|---|
| Load raw | 3 s | 5–15 min |
| Transform | 2 s | 3–8 min |
| Indexes | 1 s | 2–5 min |
| Analysis queries | 1 s | 30–90 s |
| Model + SHAP | 6 s | 3–10 min |
| Export | 1 s | 1–2 min |

---

## 6. Things that will go wrong, and the fix

**`psql: command not found`** — PATH, see section 1.

**`FATAL: password authentication failed`** — the password in `.env` doesn't match what
you set during installation. Reset it:
`psql -U postgres -c "ALTER USER postgres PASSWORD 'newpassword';"`

**`COPY` fails with a column error** — Inside Airbnb adds and removes columns between
snapshots. `src/load_raw.py` handles this: it reads each file's actual header and builds
the staging table from it, adding any new columns automatically. If it still fails, the
CSV is malformed — check it opens: `python -c "import gzip;print(gzip.open('data/raw/london_listings.csv.gz','rt').readline())"`

**`invalid input syntax for type numeric`** — a column you're casting has unexpected
text in it. Every cast in `02_transform.sql` is wrapped in `NULLIF(...,'')` and prices go
through `regexp_replace(price,'[^0-9.]','','g')`, which strips `$`, `£` and commas
regardless of which symbol the snapshot uses. If a new column breaks, wrap it the same way.

**Out of disk space** — the calendar tables are the culprit. `staging.calendar` can be
several GB. After `02_transform.sql` has run you can `TRUNCATE staging.calendar;` and
reclaim it; the core tables are what you actually query.

**`MemoryError` in `model.py`** — the model trains on `core.listings_model` (roughly
100k rows), not the calendar, so this shouldn't happen. If it does, reduce
`n_estimators`.

**The app crashes on Streamlit Cloud but works locally** — almost always memory. The
parquet files in `data/dashboard/` must stay small; `export_for_app.py` prints the total
and warns above 50 MB.

---

## 7. Deploying

1. `pip freeze > requirements.txt` is **not** what you want for deployment. Use the
   supplied `requirements-app.txt` — it excludes `psycopg2-binary` and `SQLAlchemy`,
   which the deployed app doesn't need and which can fail the build.
2. Rename it: on Streamlit Cloud the file must be called `requirements.txt` at the repo
   root, so either rename `requirements-app.txt` or set it in the app's advanced settings.
3. Push to GitHub. **Run `git status` and read it** before committing — if anything under
   `data/raw/` or a `.env` appears, stop and fix `.gitignore`. A password in git history
   is painful to remove.
4. `data/dashboard/*.parquet` and `outputs/price_model.joblib` **must** be committed —
   the deployed app has no database. The `.gitignore` is already written to allow them.
5. share.streamlit.io → sign in with GitHub → New app → pick the repo → main branch →
   `app/dashboard.py` → Deploy. First build takes 5–10 minutes.
6. Open the resulting URL on your phone before you post it anywhere.

---

## 8. What each file does

| File | Purpose |
|---|---|
| `src/db.py` | The only place that knows the database connection. Reads `.env`. |
| `src/load_raw.py` | Header-driven bulk load of the gzipped CSVs into `staging`. |
| `src/model.py` | Trains ridge + XGBoost against a neighbourhood-median baseline, writes SHAP plots. |
| `src/export_for_app.py` | Writes the small parquet files the dashboard reads. |
| `src/make_fake_sample_data.py` | Generates realistically messy fake data for testing. |
| `sql/01_schema.sql` | `staging` and `core` schemas, tables, keys. |
| `sql/02_transform.sql` | All cleaning and typing. Staging text → core typed. |
| `sql/03_views.sql` | `listing_features`, `listings_model` (outlier rules), `listing_performance`. |
| `sql/04_indexes.sql` | Indexes, run after loading. |
| `sql/analysis/q01`–`q10` | The ten analysis queries, one question each. |
| `app/dashboard.py` | Five-tab Streamlit dashboard. |
| `run_all.sh` | Runs steps 1–8 in order and stops on the first error. |
