-- Seasonality. Inside Airbnb's calendar no longer publishes nightly prices,
-- so this tracks OCCUPANCY (share of nights not available) rather than price.
--
-- IMPORTANT: restricted to listings with availability_365 > 0. A listing that
-- is never bookable shows every night as unavailable, so including them counts
-- dormant stock as fully occupied. In London that is 26,521 of 92,638 listings
-- and it inflated the headline occupancy figure by roughly 16 points.
--
-- Remaining caveat: a night can be unavailable because it is booked OR because
-- the host blocked it, so this is still an upper bound on true occupancy.
SELECT l.city,
       date_trunc('month', c.stay_date)::date       AS month,
       count(*)                                     AS nights_offered,
       count(*) FILTER (WHERE NOT c.is_available)   AS nights_unavailable,
       round(100.0 * count(*) FILTER (WHERE NOT c.is_available) / count(*), 1)
                                                    AS occupancy_pct
FROM core.calendar c
JOIN core.listings l USING (listing_id)
WHERE l.availability_365 > 0
GROUP BY l.city, 2
ORDER BY l.city, month;
