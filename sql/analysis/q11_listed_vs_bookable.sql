-- Listed vs bookable supply.
-- A listing with no price in the snapshot is one Inside Airbnb could not read a
-- rate from, which in practice means it had no bookable nights. Zero availability
-- may mean fully booked OR blocked by the host; across a full year the latter is
-- far more likely, so this is reported as "not bookable", not "dormant".
SELECT city,
       count(*)                                                        AS listed,
       count(*) FILTER (WHERE availability_365 > 0)                    AS bookable,
       count(*) FILTER (WHERE availability_365 = 0)                    AS not_bookable,
       round(100.0 * count(*) FILTER (WHERE availability_365 = 0) / count(*), 1)
                                                                       AS pct_not_bookable,
       round(avg(number_of_reviews) FILTER (WHERE availability_365 > 0), 1) AS avg_reviews_bookable,
       round(avg(number_of_reviews) FILTER (WHERE availability_365 = 0), 1) AS avg_reviews_not
FROM core.listings
GROUP BY city
ORDER BY listed DESC;
