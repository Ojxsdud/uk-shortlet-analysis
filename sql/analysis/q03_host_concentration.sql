WITH host_size AS (
  SELECT host_id, city, count(*) AS n FROM core.listings_model GROUP BY host_id, city),
bucketed AS (
  SELECT city, CASE WHEN n=1 THEN '1 listing' WHEN n BETWEEN 2 AND 4 THEN '2-4'
                    WHEN n BETWEEN 5 AND 20 THEN '5-20' ELSE '21+' END AS host_bucket,
         count(*) AS hosts, sum(n) AS listings
  FROM host_size GROUP BY city,2)
SELECT city, host_bucket, hosts, listings,
       round(100.0*listings/sum(listings) OVER (PARTITION BY city),1) AS pct_of_supply,
       round(100.0*hosts/sum(hosts) OVER (PARTITION BY city),1) AS pct_of_hosts
FROM bucketed ORDER BY city,
  CASE host_bucket WHEN '1 listing' THEN 1 WHEN '2-4' THEN 2 WHEN '5-20' THEN 3 ELSE 4 END;
