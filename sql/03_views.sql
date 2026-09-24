CREATE OR REPLACE VIEW core.listing_features AS
SELECT
    l.listing_id,
    COALESCE(bool_or(a.amenity ILIKE '%wifi%'), false)             AS has_wifi,
    COALESCE(bool_or(a.amenity ILIKE '%air conditioning%'), false) AS has_aircon,
    COALESCE(bool_or(a.amenity ILIKE '%free%parking%'), false)     AS has_free_parking,
    COALESCE(bool_or(a.amenity ILIKE '%washer%'), false)           AS has_washer,
    COALESCE(bool_or(a.amenity ILIKE '%dishwasher%'), false)       AS has_dishwasher,
    COALESCE(bool_or(a.amenity ILIKE '%hot tub%'), false)          AS has_hot_tub,
    COALESCE(bool_or(a.amenity ILIKE '%self check-in%'), false)    AS has_self_checkin,
    COALESCE(bool_or(a.amenity ILIKE '%workspace%'), false)        AS has_workspace,
    COALESCE(bool_or(a.amenity ILIKE '%pets allowed%'), false)     AS pets_allowed,
    COALESCE(bool_or(a.amenity ILIKE '%elevator%'), false)         AS has_lift,
    count(a.amenity)                                               AS amenity_count
FROM core.listings l
LEFT JOIN core.amenities a USING (listing_id)
GROUP BY l.listing_id;

CREATE OR REPLACE VIEW core.listings_model AS
WITH bounds AS (
    SELECT city, percentile_cont(0.99) WITHIN GROUP (ORDER BY price_gbp) AS p99
    FROM core.listings WHERE price_gbp > 0 GROUP BY city
)
SELECT l.*
FROM core.listings l
JOIN bounds b ON b.city = l.city
WHERE l.price_gbp > 0
  AND l.price_gbp <= b.p99
  AND l.minimum_nights <= 30
  AND l.accommodates <= 16;

-- Calendar no longer carries nightly prices, so revenue is estimated as
--   booked nights x the listing's CURRENT advertised rate.
-- This ignores seasonal and weekend pricing, so it is a rougher proxy than
-- before. State that wherever the number is shown.
CREATE OR REPLACE VIEW core.listing_performance AS
SELECT c.listing_id,
       l.city,
       l.neighbourhood,
       count(*) FILTER (WHERE NOT c.is_available)  AS nights_booked,
       count(*)                                    AS nights_in_window,
       round(100.0 * count(*) FILTER (WHERE NOT c.is_available) / count(*), 1)
                                                   AS occupancy_pct,
       max(l.price_gbp)                            AS advertised_price,
       round(count(*) FILTER (WHERE NOT c.is_available) * max(l.price_gbp), 2)
                                                   AS est_revenue
FROM core.calendar c
JOIN core.listings l USING (listing_id)
GROUP BY c.listing_id, l.city, l.neighbourhood;
