-- =============================================================================
-- SAHIDAWA SCHEMA — Run this in Supabase SQL Editor
-- Project: zbnbjgcvwhqjsauffvyn
-- =============================================================================

-- Enable required extensions (pg_trgm for trigram similarity, postgis for geo)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: salts (1649 rows)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.salts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500) NOT NULL UNIQUE,
    synonyms TEXT[] DEFAULT '{}',
    therapeutic_class VARCHAR(200),
    is_narrow_therapeutic_index BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_salts_name ON public.salts (name);
CREATE INDEX idx_salts_name_trgm ON public.salts USING gin (name gin_trgm_ops);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: drugs (245988 rows)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.drugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name VARCHAR(300) NOT NULL,
    manufacturer VARCHAR(300) NOT NULL,
    salt_id UUID NOT NULL REFERENCES public.salts(id),
    strength VARCHAR(100) NOT NULL,
    dosage_form VARCHAR(100) NOT NULL,
    pack_size VARCHAR(50),
    mrp NUMERIC(10, 2) NOT NULL,
    price_per_unit NUMERIC(10, 4),
    source VARCHAR(100),
    is_discontinued BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drugs_brand_name ON public.drugs (brand_name);
CREATE INDEX idx_drugs_brand_name_trgm ON public.drugs USING gin (brand_name gin_trgm_ops);
CREATE INDEX idx_drugs_salt_id ON public.drugs (salt_id);
CREATE INDEX idx_drugs_mrp ON public.drugs (mrp);
CREATE INDEX idx_drugs_strength ON public.drugs (strength);
CREATE INDEX idx_drugs_salt_strength ON public.drugs (salt_id, strength);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: jan_aushadhi_stores (7742 rows)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.jan_aushadhi_stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(500),
    address TEXT NOT NULL,
    city VARCHAR(200),
    district VARCHAR(200),
    state VARCHAR(200),
    pin_code VARCHAR(10),
    phone VARCHAR(20),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location GEOGRAPHY(POINT, 4326) GENERATED ALWAYS AS (
        CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        THEN ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
        ELSE NULL END
    ) STORED,
    status VARCHAR(50) DEFAULT 'Operational',
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stores_pin_code ON public.jan_aushadhi_stores (pin_code);
CREATE INDEX idx_stores_location ON public.jan_aushadhi_stores USING gist (location);
CREATE INDEX idx_stores_district ON public.jan_aushadhi_stores (district);
CREATE INDEX idx_stores_state ON public.jan_aushadhi_stores (state);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: nppa_ceiling_prices (623 rows)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.nppa_ceiling_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    salt_name VARCHAR(500) NOT NULL,
    dosage_form VARCHAR(100),
    strength VARCHAR(100),
    unit VARCHAR(50),
    ceiling_price NUMERIC(12, 4) NOT NULL,
    so_number VARCHAR(100),
    so_date VARCHAR(50),
    effective_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nppa_salt ON public.nppa_ceiling_prices (salt_name);
CREATE INDEX idx_nppa_salt_form_strength ON public.nppa_ceiling_prices (salt_name, dosage_form, strength);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: query_logs (existing from earlier models)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_hash VARCHAR(100) NOT NULL,
    query_text TEXT NOT NULL,
    response_data JSONB,
    response_time_ms INTEGER,
    session_pin_code VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_logs_phone ON public.query_logs (phone_hash);
CREATE INDEX IF NOT EXISTS idx_query_logs_created ON public.query_logs (created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: waitlist (email signups from landing page)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.waitlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(320) NOT NULL UNIQUE,
    name VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_waitlist_email ON public.waitlist (email);
CREATE INDEX IF NOT EXISTS idx_waitlist_created ON public.waitlist (created_at DESC);

-- =============================================================================
-- RLS — Allow anonymous read access
-- =============================================================================
ALTER TABLE public.salts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drugs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jan_aushadhi_stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nppa_ceiling_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.query_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_anon_read" ON public.salts FOR SELECT USING (true);
CREATE POLICY "allow_anon_read" ON public.drugs FOR SELECT USING (true);
CREATE POLICY "allow_anon_read" ON public.jan_aushadhi_stores FOR SELECT USING (true);
CREATE POLICY "allow_anon_read" ON public.nppa_ceiling_prices FOR SELECT USING (true);
CREATE POLICY "allow_anon_insert" ON public.query_logs FOR INSERT WITH CHECK (true);

ALTER TABLE public.waitlist ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_anon_insert" ON public.waitlist FOR INSERT WITH CHECK (true);

-- =============================================================================
-- Functions
-- =============================================================================

-- Find nearest stores by lat/lng (PostGIS)
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

-- Find stores by pin with prefix fallback
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