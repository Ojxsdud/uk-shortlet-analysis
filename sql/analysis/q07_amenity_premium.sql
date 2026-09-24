WITH base AS (
  SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY price_gbp) AS median_all
  FROM core.listings_model WHERE city='london')
SELECT a.amenity, count(*) AS listings_with,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY l.price_gbp)::numeric,2) AS median_with,
       round(min(b.median_all)::numeric,2) AS median_all_listings
FROM core.amenities a
JOIN core.listings_model l USING (listing_id) CROSS JOIN base b
WHERE l.city='london' GROUP BY a.amenity HAVING count(*)>=100
ORDER BY median_with DESC LIMIT 25;
