SELECT city, count(*) AS listings, count(DISTINCT host_id) AS hosts,
       round(avg(price_gbp),2) AS mean_price,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY price_gbp)::numeric,2) AS median_price,
       round(avg(accommodates),1) AS avg_sleeps,
       round(100.0*count(*) FILTER (WHERE room_type='Entire home/apt')/count(*),1) AS pct_entire_home
FROM core.listings_model GROUP BY city ORDER BY listings DESC;
