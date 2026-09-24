"""Export the small parquet files the dashboard reads.
The deployed app has NO database, so everything it needs must be here and
must stay small enough for Streamlit Cloud's ~1 GB memory limit."""
import os, pandas as pd
from sqlalchemy import text
from db import engine

ENGINE = engine()
OUT = "data/dashboard"
os.makedirs(OUT, exist_ok=True)

def sql(path):
    return open(path).read()

EXPORTS = {
  "listings": """
     SELECT l.listing_id, l.host_id, l.city, l.neighbourhood, l.latitude, l.longitude,
            l.room_type, l.property_type, l.accommodates, l.bedrooms, l.bathrooms,
            l.price_gbp, l.minimum_nights, l.availability_365, l.number_of_reviews,
            l.rating, h.is_superhost, p.occupancy_pct, p.est_revenue
     FROM core.listings_model l
     JOIN core.hosts h USING (host_id)
     LEFT JOIN core.listing_performance p USING (listing_id)""",
  "price_summary": """
     SELECT city,
            count(*)                                                        AS n,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY price_gbp)::numeric AS p25,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY price_gbp)::numeric AS median,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY price_gbp)::numeric AS p75,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY price_gbp)::numeric AS p90,
            avg(price_gbp)::numeric                                          AS mean
     FROM core.listings_model GROUP BY city""",
  "distance_price": """
     SELECT city, bucket_km,
            count(*) AS n,
            round(percentile_cont(0.5) WITHIN GROUP (ORDER BY price_gbp)::numeric, 2) AS median_price
     FROM (
        SELECT city, price_gbp,
               width_bucket(
                 6371 * 2 * asin(sqrt(
                   power(sin(radians(latitude - c.lat)/2), 2) +
                   cos(radians(c.lat)) * cos(radians(latitude)) *
                   power(sin(radians(longitude - c.lon)/2), 2)))
               , 0, 25, 25) AS bucket_km
        FROM core.listings_model
        JOIN (VALUES ('london',51.5074,-0.1278),
                     ('edinburgh',55.9533,-3.1883),
                     ('manchester',53.4794,-2.2453)) AS c(cty,lat,lon)
          ON c.cty = city
     ) t GROUP BY city, bucket_km HAVING count(*) >= 25 ORDER BY city, bucket_km""",
  "host_concentration": sql("sql/analysis/q03_host_concentration.sql"),
  "revenue_curve":      sql("sql/analysis/q04_revenue_concentration.sql"),
  "seasonality":        sql("sql/analysis/q05_seasonality.sql"),
  "weekend":            sql("sql/analysis/q06_weekend_premium.sql"),
  "neighbourhoods":     sql("sql/analysis/q02_neighbourhoods.sql"),
  "market_shape":       sql("sql/analysis/q01_market_shape.sql"),
}
if os.path.exists("sql/analysis/q11_listed_vs_bookable.sql"):
    EXPORTS["listed_vs_bookable"] = sql("sql/analysis/q11_listed_vs_bookable.sql")

for name, q in EXPORTS.items():
    df = pd.read_sql(text(q), ENGINE)
    for c in df.columns:
        if df[c].dtype == "object":
            try: df[c] = pd.to_numeric(df[c])
            except (TypeError, ValueError): pass
    path = f"{OUT}/{name}.parquet"
    df.to_parquet(path, index=False, compression="snappy")
    print(f"{name:<22}{len(df):>8,} rows   {os.path.getsize(path)/1e6:>6.2f} MB")

total = sum(os.path.getsize(f"{OUT}/{f}") for f in os.listdir(OUT))
print(f"\nTOTAL {total/1e6:.2f} MB  (keep under ~50 MB for GitHub + Streamlit Cloud)")
