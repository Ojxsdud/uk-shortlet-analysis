TRUNCATE core.amenities, core.calendar, core.reviews, core.listings, core.hosts CASCADE;

INSERT INTO core.hosts
SELECT DISTINCT ON (host_id::bigint)
    host_id::bigint,
    NULLIF(host_since,'')::date,
    CASE host_is_superhost WHEN 't' THEN true WHEN 'f' THEN false ELSE NULL END,
    CASE host_identity_verified WHEN 't' THEN true WHEN 'f' THEN false ELSE NULL END,
    NULLIF(REPLACE(host_response_rate,'%',''),'')::numeric,
    NULLIF(REPLACE(host_acceptance_rate,'%',''),'')::numeric,
    NULLIF(host_listings_count,'')::numeric::int
FROM staging.listings
WHERE host_id ~ '^[0-9]+$'
ORDER BY host_id::bigint, last_scraped DESC;

INSERT INTO core.listings
SELECT
    id::bigint, host_id::bigint, city, neighbourhood_cleansed,
    NULLIF(latitude,'')::numeric, NULLIF(longitude,'')::numeric,
    property_type, room_type,
    NULLIF(accommodates,'')::numeric::smallint,
    NULLIF(bedrooms,'')::numeric::smallint,
    NULLIF(beds,'')::numeric::smallint,
    CASE WHEN bathrooms_text ILIKE '%half%' THEN 0.5
         ELSE NULLIF(substring(bathrooms_text from '^[0-9]+\.?[0-9]*'),'')::numeric END,
    NULLIF(regexp_replace(price, '[^0-9.]', '', 'g'), '')::numeric,
    NULLIF(minimum_nights,'')::numeric::int,
    NULLIF(maximum_nights,'')::numeric::int,
    NULLIF(availability_365,'')::numeric::smallint,
    NULLIF(number_of_reviews,'')::numeric::int,
    NULLIF(number_of_reviews_ltm,'')::numeric::int,
    NULLIF(first_review,'')::date, NULLIF(last_review,'')::date,
    NULLIF(review_scores_rating,'')::numeric,
    NULLIF(review_scores_cleanliness,'')::numeric,
    NULLIF(review_scores_location,'')::numeric,
    NULLIF(review_scores_value,'')::numeric,
    CASE instant_bookable WHEN 't' THEN true WHEN 'f' THEN false ELSE NULL END,
    NULLIF(reviews_per_month,'')::numeric,
    NULLIF(last_scraped,'')::date
FROM staging.listings
WHERE id ~ '^[0-9]+$' AND host_id ~ '^[0-9]+$'
ON CONFLICT (listing_id) DO NOTHING;

INSERT INTO core.amenities
SELECT DISTINCT id::bigint, amenity
FROM staging.listings, LATERAL json_array_elements_text(amenities::json) AS amenity
WHERE id ~ '^[0-9]+$' AND amenities LIKE '[%'
ON CONFLICT DO NOTHING;

INSERT INTO core.calendar
SELECT listing_id::bigint, date::date,
       CASE available WHEN 't' THEN true WHEN 'f' THEN false ELSE NULL END,
       NULLIF(minimum_nights,'')::numeric::int,
       city
FROM staging.calendar
WHERE listing_id ~ '^[0-9]+$'
ON CONFLICT (listing_id, stay_date) DO NOTHING;


