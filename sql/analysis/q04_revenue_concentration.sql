WITH ranked AS (
  SELECT p.listing_id, p.city, p.est_revenue,
         ROW_NUMBER() OVER (PARTITION BY p.city ORDER BY p.est_revenue DESC) AS rn,
         count(*) OVER (PARTITION BY p.city) AS total_listings,
         sum(p.est_revenue) OVER (PARTITION BY p.city) AS city_revenue
  FROM core.listing_performance p WHERE p.est_revenue > 0),
cumulative AS (
  SELECT city, rn, total_listings, city_revenue,
         sum(est_revenue) OVER (PARTITION BY city ORDER BY rn) AS running_revenue
  FROM ranked)
SELECT city, round(100.0*rn/total_listings,1) AS pct_of_listings,
       round(100.0*running_revenue/city_revenue,1) AS pct_of_revenue
FROM cumulative WHERE rn % 200 = 0 ORDER BY city, rn;
