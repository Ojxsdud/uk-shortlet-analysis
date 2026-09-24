CREATE INDEX IF NOT EXISTS idx_listings_city     ON core.listings(city);
CREATE INDEX IF NOT EXISTS idx_listings_nbhd     ON core.listings(city, neighbourhood);
CREATE INDEX IF NOT EXISTS idx_listings_host     ON core.listings(host_id);
CREATE INDEX IF NOT EXISTS idx_listings_roomtype ON core.listings(room_type);
CREATE INDEX IF NOT EXISTS idx_calendar_date     ON core.calendar(stay_date);
CREATE INDEX IF NOT EXISTS idx_calendar_listing  ON core.calendar(listing_id);
CREATE INDEX IF NOT EXISTS idx_reviews_listing   ON core.reviews(listing_id, review_date);
CREATE INDEX IF NOT EXISTS idx_amenities_amenity ON core.amenities(amenity);
ANALYZE;
