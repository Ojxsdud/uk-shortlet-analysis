SELECT * FROM (
  SELECT city, neighbourhood, count(*) AS listings,
         round(percentile_cont(0.5) WITHIN GROUP (ORDER BY price_gbp)::numeric,2) AS median_price,
         RANK() OVER (PARTITION BY city ORDER BY percentile_cont(0.5) WITHIN GROUP (ORDER BY price_gbp) DESC) AS price_rank,
         round(100.0*count(*)/sum(count(*)) OVER (PARTITION BY city),2) AS pct_of_city_supply
  FROM core.listings_model GROUP BY city, neighbourhood HAVING count(*)>=30
) t WHERE price_rank<=10 ORDER BY city, price_rank;
