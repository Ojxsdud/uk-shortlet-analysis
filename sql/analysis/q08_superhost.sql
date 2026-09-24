SELECT l.city, h.is_superhost, count(*) AS listings,
       round(avg(l.price_gbp),2) AS avg_price, round(avg(l.rating),2) AS avg_rating,
       round(avg(p.occupancy_pct),1) AS avg_occupancy
FROM core.listings_model l JOIN core.hosts h USING (host_id)
LEFT JOIN core.listing_performance p USING (listing_id)
GROUP BY l.city, h.is_superhost ORDER BY l.city, h.is_superhost NULLS LAST;
