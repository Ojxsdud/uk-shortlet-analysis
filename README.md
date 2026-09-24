# UK Short-Let Market Analysis

**[→ Live dashboard](ADD_YOUR_STREAMLIT_URL_HERE)**

An end-to-end analysis of 105,812 Airbnb listings across London, Edinburgh and
Greater Manchester: a PostgreSQL warehouse built from raw scrape files, eleven
SQL analyses, a gradient-boosted price model with SHAP explanations, and an
interactive dashboard.

*(Add a screenshot of the map tab here — `![Dashboard](docs/map.png)`)*

---

## Three findings

**1. A small minority of hosts hold most of the supply.**
In London, the 6.4% of hosts with five or more listings hold **40.5% of live
listings**. The 256 hosts with 21 or more — under 1% of all hosts — hold 10,798
listings between them. Greater Manchester is similar (7.9% of hosts, 38.8% of
supply); Edinburgh is less concentrated (4.1% and 27.4%).

**2. Roughly a third of London's advertised stock cannot be booked.**
26,521 of London's 92,638 listings show **zero availability across the next 365
days**, and they average 13.1 reviews against 28.6 for bookable listings.
Edinburgh's equivalent figure is 5.3%; Greater Manchester's is effectively zero.
Headline counts of "Airbnbs in London" include all of them.

**3. Edinburgh is more expensive than London.**
Median nightly rates: **Edinburgh £230, London £180, Greater Manchester £115**.
All three cities were scraped within the same two-week window, so this is a
like-for-like comparison — though late June is the run-up to Edinburgh's
festival season, and this is not an annual average.

---

## Data

| | |
|---|---|
| Source | [Inside Airbnb](https://insideairbnb.com), CC BY 4.0 |
| Snapshot | 19 June – 2 July 2026 |
| Cities | London, Edinburgh, Greater Manchester |
| Listings | 105,812 |
| Hosts | 58,982 |
| Calendar rows | 38,691,461 |
| Amenity rows | 3,097,363 |

Review text was deliberately not loaded. It is 364 MB of the source data, no
analysis here uses it, and it contains guest names — personal data with no
reason to be in this database.

### Listings per city

| City | Advertised | After exclusions | Excluded |
|---|---|---|---|
| London | 92,638 | 61,173 | 34.0% |
| Greater Manchester | 6,930 | 6,714 | 3.1% |
| Edinburgh | 6,244 | 5,536 | 11.3% |

London's exclusion rate is high because 30,398 of its listings carry no price.
Those turn out to be listings with no bookable nights — Inside Airbnb can only
read a rate where there is one to read. The exclusion is therefore an
"is this listing live?" filter, which is what finding 2 is about.

---

## Method

```
Inside Airbnb CSVs  →  staging (all text, schema derived from each file's header)
                    →  core    (typed, constrained, foreign keys)
                    →  views   (exclusion rules, derived measures)
                    →  11 analysis queries  →  CSV
                    →  XGBoost + SHAP       →  model artefacts
                    →  aggregated parquet   →  Streamlit dashboard
```

The loader builds its staging tables from each file's actual header rather than
a fixed DDL. That is not defensive programming for its own sake — see below.

---

## Model

Predicts log nightly price. Trained on 73,423 listings, 80/20 split.

| Model | MAE | Median AE | R² (log) |
|---|---|---|---|
| Baseline — neighbourhood median | £112.86 | £73.75 | 0.202 |
| Ridge regression | £68.27 | £36.10 | 0.716 |
| **XGBoost** | **£58.03** | **£30.33** | **0.780** |

The baseline is included because a model without one proves nothing. XGBoost
beats a neighbourhood median comfortably, which is what justifies the
complexity.

Strongest features by mean |SHAP|:

1. Room type — entire home vs private room
2. **Distance from the city centre**
3. Guests accommodated
4. City (Greater Manchester being systematically cheaper)
5. Bedrooms
6. Bathrooms

Mean error (£58) is far above median error (£30) because price is
right-skewed — the model is much less accurate on expensive listings.

**What this model is not.** It predicts *advertised* price, not market value and
not what a listing should charge. It learns what hosts currently ask, including
where they ask wrongly. A listing priced below its estimate may be underpriced,
or may have a defect no column here captures.

---

## The source schema changed mid-project

Three published fields disappeared from this snapshot relative to earlier ones:

| Field | Consequence |
|---|---|
| `calendar.price`, `calendar.adjusted_price` | No per-night rates. Seasonality is measured as occupancy, not price; revenue is estimated as booked nights × the listing's current advertised rate |
| `listings.instant_bookable` | Empty for all 105,812 rows |
| `listings.host_since` | Empty for all 105,812 rows |

The last two were being silently imputed from nothing — scikit-learn warns, but
the model trains anyway and the features contribute noise. `model.py` now
derives its feature list from the data and reports what it dropped. Removing
both changed R² by less than 0.001.

This is why the loader is header-driven. Between the calendar losing two columns
and the listings file gaining fifteen, a fixed DDL would have failed twice.

---

## Limitations

- **Scraped, not transactional.** Inside Airbnb observes public listing pages. It
  is not booking data.
- **Availability is not occupancy.** A night shows as unavailable whether it was
  booked or blocked by the host. Every occupancy figure here is an upper bound.
- **Revenue is doubly estimated** — booked nights (upper bound) × current
  advertised rate (ignores seasonal pricing). The shape of the concentration
  curve is sound; the pound amounts are indicative.
- **One snapshot.** A fortnight in June 2026. No trend, no seasonality beyond
  what the forward calendar shows.
- **Advertised ≠ transacted price.** Discounts, cleaning fees and platform fees
  are not visible.
- **Availability above 90 nights is not evidence of a breach** of London's
  short-let rules. Hosts may advertise more nights than they let, and exemptions
  exist.

---

## Running it

Requires PostgreSQL 16 and Python 3.11+. Full setup in [`SETUP.md`](SETUP.md).

```bash
python -m venv venv && source venv/bin/activate    # .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
cp .env.example .env                               # add your database password

psql -U postgres -c "CREATE DATABASE shortlet;"
bash run_all.sh
streamlit run app/dashboard.py
```

Download the four files per city from
[insideairbnb.com/get-the-data](https://insideairbnb.com/get-the-data) into
`data/raw/`, named `<city>_listings.csv.gz` and so on.

To verify the pipeline before downloading anything, `python
src/make_fake_sample_data.py` generates correctly-shaped test data and the whole
thing runs on it in under a minute.

---

## Layout

| Path | |
|---|---|
| `src/db.py` | Database connection, read from `.env` |
| `src/load_raw.py` | Header-driven bulk load into `staging` |
| `src/model.py` | Baseline, ridge and XGBoost; SHAP plots |
| `src/export_for_app.py` | Aggregates for the dashboard |
| `sql/01_schema.sql` | Schemas, tables, keys |
| `sql/02_transform.sql` | Cleaning and typing |
| `sql/03_views.sql` | Exclusion rules, derived measures |
| `sql/analysis/q01`–`q11` | One question per file |
| `app/dashboard.py` | Five-tab Streamlit dashboard |

---

Data: Inside Airbnb, 19 June – 2 July 2026, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Built with PostgreSQL, pandas, scikit-learn, XGBoost, SHAP, Plotly and Streamlit.
