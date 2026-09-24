-- Weekend effect. With no calendar prices, this measures how much more of
-- Friday/Saturday stock is taken compared with mid-week.
--
-- Restricted to listings with availability_365 > 0, for the reason given in
-- q05: never-bookable listings read as 100% occupied on every night.
SELECT l.city,
       round(100.0 * count(*) FILTER (WHERE NOT c.is_available AND EXTRACT(dow FROM c.stay_date) IN (5,6))
             / NULLIF(count(*) FILTER (WHERE EXTRACT(dow FROM c.stay_date) IN (5,6)), 0), 1)
           AS weekend_occupancy_pct,
       round(100.0 * count(*) FILTER (WHERE NOT c.is_available AND EXTRACT(dow FROM c.stay_date) NOT IN (5,6))
             / NULLIF(count(*) FILTER (WHERE EXTRACT(dow FROM c.stay_date) NOT IN (5,6)), 0), 1)
           AS weekday_occupancy_pct,
       round(
         (100.0 * count(*) FILTER (WHERE NOT c.is_available AND EXTRACT(dow FROM c.stay_date) IN (5,6))
          / NULLIF(count(*) FILTER (WHERE EXTRACT(dow FROM c.stay_date) IN (5,6)), 0))
         -
         (100.0 * count(*) FILTER (WHERE NOT c.is_available AND EXTRACT(dow FROM c.stay_date) NOT IN (5,6))
          / NULLIF(count(*) FILTER (WHERE EXTRACT(dow FROM c.stay_date) NOT IN (5,6)), 0))
       , 1) AS weekend_uplift_pts
FROM core.calendar c
JOIN core.listings l USING (listing_id)
WHERE l.availability_365 > 0
GROUP BY l.city
ORDER BY l.city;
