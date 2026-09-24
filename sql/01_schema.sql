DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS core CASCADE;
CREATE SCHEMA staging;
CREATE SCHEMA core;

CREATE TABLE core.hosts (
    host_id              bigint PRIMARY KEY,
    host_since           date,
    is_superhost         boolean,
    identity_verified    boolean,
    response_rate_pct    numeric(5,2),
    acceptance_rate_pct  numeric(5,2),
    listings_count       integer
);

CREATE TABLE core.listings (
    listing_id           bigint PRIMARY KEY,
    host_id              bigint REFERENCES core.hosts(host_id),
    city                 text NOT NULL,
    neighbourhood        text,
    latitude             numeric(9,6),
    longitude            numeric(9,6),
    property_type        text,
    room_type            text,
    accommodates         smallint,
    bedrooms             smallint,
    beds                 smallint,
    bathrooms            numeric(3,1),
    price_gbp            numeric(10,2),
    minimum_nights       integer,
    maximum_nights       integer,
    availability_365     smallint,
    number_of_reviews    integer,
    reviews_ltm          integer,
    first_review         date,
    last_review          date,
    rating               numeric(3,2),
    rating_cleanliness   numeric(3,2),
    rating_location      numeric(3,2),
    rating_value         numeric(3,2),
    instant_bookable     boolean,
    reviews_per_month    numeric(6,2),
    last_scraped         date
);

CREATE TABLE core.amenities (
    listing_id  bigint REFERENCES core.listings(listing_id),
    amenity     text,
    PRIMARY KEY (listing_id, amenity)
);

-- NOTE: Inside Airbnb removed price / adjusted_price from calendar.csv.
-- The calendar now tells us only WHETHER a night is available, not at what rate.
CREATE TABLE core.calendar (
    listing_id      bigint,
    stay_date       date,
    is_available    boolean,
    minimum_nights  integer,
    city            text,
    PRIMARY KEY (listing_id, stay_date)
);

CREATE TABLE core.reviews (
    review_id   bigint PRIMARY KEY,
    listing_id  bigint,
    review_date date,
    reviewer_id bigint,
    city        text
);
