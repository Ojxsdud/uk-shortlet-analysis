SELECT neighbourhood, count(*) AS entire_home_listings,
       count(*) FILTER (WHERE availability_365 > 90) AS over_90_available,
       round(100.0*count(*) FILTER (WHERE availability_365 > 90)/count(*),1) AS pct
FROM core.listings_model WHERE city='london' AND room_type='Entire home/apt'
GROUP BY neighbourhood HAVING count(*)>=50 ORDER BY pct DESC;
