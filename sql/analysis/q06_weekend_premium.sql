-- Weekend effect. With no calendar prices, this measures how much more of
-- Friday/Saturday stock is taken compared with mid-week.
SELECT city,
       round(100.0 * count(*) FILTER (WHERE NOT is_available AND EXTRACT(dow FROM stay_date) IN (5,6))
             / NULLIF(count(*) FILTER (WHERE EXTRACT(dow FROM stay_date) IN (5,6)), 0), 1)
           AS weekend_occupancy_pct,
       round(100.0 * count(*) FILTER (WHERE NOT is_available AND EXTRACT(dow FROM stay_date) NOT IN (5,6))
             / NULLIF(count(*) FILTER (WHERE EXTRACT(dow FROM stay_date) NOT IN (5,6)), 0), 1)
           AS weekday_occupancy_pct,
       round(
         (100.0 * count(*) FILTER (WHERE NOT is_available AND EXTRACT(dow FROM stay_date) IN (5,6))
          / NULLIF(count(*) FILTER (WHERE EXTRACT(dow FROM stay_date) IN (5,6)), 0))
         -
         (100.0 * count(*) FILTER (WHERE NOT is_available AND EXTRACT(dow FROM stay_date) NOT IN (5,6))
          / NULLIF(count(*) FILTER (WHERE EXTRACT(dow FROM stay_date) NOT IN (5,6)), 0))
       , 1) AS weekend_uplift_pts
FROM core.calendar
GROUP BY city
ORDER BY city;
