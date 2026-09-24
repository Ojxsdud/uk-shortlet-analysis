-- Listing growth by cohort year (proxy: date of first review).
-- NOTE: the cumulative window must run over the ALREADY-GROUPED result,
-- so the aggregation goes in a subquery. Putting sum(count(*)) OVER
-- (ORDER BY date_trunc('year', first_review)) in the grouped query itself
-- fails: the window ORDER BY expression is not in the GROUP BY clause.
SELECT city, cohort_year, new_listings,
       sum(new_listings) OVER (PARTITION BY city ORDER BY cohort_year) AS cumulative
FROM (
    SELECT city,
           date_trunc('year', first_review)::date AS cohort_year,
           count(*) AS new_listings
    FROM core.listings_model
    WHERE first_review IS NOT NULL
    GROUP BY city, 2
) t
ORDER BY city, cohort_year;
