-- Create the missing PostGIS store functions in Supabase
-- Run this in SQL Editor after supabase_schema.sql

-- Function: find_stores_by_pin_with_prefix
CREATE OR REPLACE FUNCTION public.find_stores_by_pin_with_prefix(
    pin VARCHAR(10),
    store_limit INTEGER DEFAULT 5
)
RETURNS TABLE(
    store_code VARCHAR(50), name VARCHAR(500), address TEXT,
    city VARCHAR(200), district VARCHAR(200), state VARCHAR(200),
    pin_code VARCHAR(10), phone VARCHAR(20), match_type VARCHAR(10)
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT s.store_code, s.name, s.address, s.city, s.district, s.state, s.pin_code, s.phone, 'exact'::VARCHAR
    FROM public.jan_aushadhi_stores s WHERE s.pin_code = pin LIMIT store_limit;

    IF (SELECT count(*) FROM public.jan_aushadhi_stores s WHERE s.pin_code = pin) < store_limit THEN
        RETURN QUERY
        SELECT s.store_code, s.name, s.address, s.city, s.district, s.state, s.pin_code, s.phone, 'prefix'::VARCHAR
        FROM public.jan_aushadhi_stores s
        WHERE s.pin_code LIKE (LEFT(pin, 3) || '%') AND s.pin_code != pin
        ORDER BY s.pin_code LIMIT store_limit;
    END IF;
END;
$$;

-- Function: find_nearest_stores (PostGIS)
CREATE OR REPLACE FUNCTION public.find_nearest_stores(
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    radius_km DOUBLE PRECISION DEFAULT 10,
    store_limit INTEGER DEFAULT 5
)
RETURNS TABLE(
    store_code VARCHAR(50), name VARCHAR(500), address TEXT,
    city VARCHAR(200), district VARCHAR(200), state VARCHAR(200),
    pin_code VARCHAR(10), phone VARCHAR(20), distance_meters DOUBLE PRECISION
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.store_code, s.name, s.address,
        s.city, s.district, s.state, s.pin_code, s.phone,
        ST_Distance(s.location, ST_MakePoint(lng, lat)::geography) AS distance_meters
    FROM public.jan_aushadhi_stores s
    WHERE s.location IS NOT NULL
      AND ST_DWithin(s.location, ST_MakePoint(lng, lat)::geography, radius_km * 1000)
    ORDER BY s.location <-> ST_MakePoint(lng, lat)::geography
    LIMIT store_limit;
END;
$$;