-- Seasonality. Inside Airbnb's calendar no longer publishes nightly prices,
-- so this tracks OCCUPANCY (share of nights not available) rather than price.
-- Caveat: a night can be unavailable because it is booked OR because the host
-- blocked it, so this is an upper bound on true occupancy.
SELECT city,
       date_trunc('month', stay_date)::date AS month,
       count(*)                                    AS nights_offered,
       count(*) FILTER (WHERE NOT is_available)    AS nights_unavailable,
       round(100.0 * count(*) FILTER (WHERE NOT is_available) / count(*), 1)
                                                   AS occupancy_pct
FROM core.calendar
GROUP BY city, 2
ORDER BY city, month;
