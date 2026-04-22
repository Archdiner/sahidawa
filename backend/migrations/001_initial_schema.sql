-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS postgis;

-- =============================================================================
-- SAHIDAWA SCHEMA MIGRATION
-- Applied to: Supabase PostgreSQL (project ref: zbnbjgcvwhqjsauffvyn)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: salts
-- Master list of salt/composition names (the active pharmaceutical ingredient)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.salts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500) NOT NULL UNIQUE,
    synonyms TEXT[] DEFAULT '{}',
    therapeutic_class VARCHAR(200),
    is_narrow_therapeutic_index BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_salts_name ON public.salts (name);
CREATE INDEX IF NOT EXISTS idx_salts_name_trgm ON public.salts USING gin (name gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- Table: drugs
-- Branded pharmaceutical products with pricing
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.drugs (
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

CREATE INDEX IF NOT EXISTS idx_drugs_brand_name ON public.drugs (brand_name);
CREATE INDEX IF NOT EXISTS idx_drugs_brand_name_trgm ON public.drugs USING gin (brand_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_drugs_salt_id ON public.drugs (salt_id);
CREATE INDEX IF NOT EXISTS idx_drugs_mrp ON public.drugs (mrp);
CREATE INDEX IF NOT EXISTS idx_drugs_strength ON public.drugs (strength);

-- Composite index for salt+strength lookups (generic substitution)
CREATE INDEX IF NOT EXISTS idx_drugs_salt_strength ON public.drugs (salt_id, strength);

-- -----------------------------------------------------------------------------
-- Table: jan_aushadhi_stores
-- Jan Aushadhi Kendras (government generic medicine stores) with geo coordinates
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.jan_aushadhi_stores (
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

-- Standard index by pin code
CREATE INDEX IF NOT EXISTS idx_stores_pin_code ON public.jan_aushadhi_stores (pin_code);

-- PostGIS spatial index for radius queries (lat/lng based)
CREATE INDEX IF NOT EXISTS idx_stores_location ON public.jan_aushadhi_stores USING gist (location);

-- Index on district/state for area-based queries
CREATE INDEX IF NOT EXISTS idx_stores_district ON public.jan_aushadhi_stores (district);
CREATE INDEX IF NOT EXISTS idx_stores_state ON public.jan_aushadhi_stores (state);

-- -----------------------------------------------------------------------------
-- Table: nppa_ceiling_prices
-- NPPA (National Pharmaceutical Pricing Authority) ceiling prices by salt/strength
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.nppa_ceiling_prices (
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

-- Index for fast ceiling price lookups
CREATE INDEX IF NOT EXISTS idx_nppa_salt ON public.nppa_ceiling_prices (salt_name);
CREATE INDEX IF NOT EXISTS idx_nppa_salt_form_strength ON public.nppa_ceiling_prices (salt_name, dosage_form, strength);

-- -----------------------------------------------------------------------------
-- Table: query_logs (existing table, keep as-is)
-- -----------------------------------------------------------------------------
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

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all public tables
ALTER TABLE public.salts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drugs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jan_aushadhi_stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nppa_ceiling_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.query_logs ENABLE ROW LEVEL SECURITY;

-- Drugs, salts, NPPA, stores: read-only public access (no auth required for reads)
-- This allows anonymous API access for drug lookups and store searches

CREATE POLICY "Allow anon read salts" ON public.salts
    FOR SELECT USING (true);

CREATE POLICY "Allow anon read drugs" ON public.drugs
    FOR SELECT USING (true);

CREATE POLICY "Allow anon read stores" ON public.jan_aushadhi_stores
    FOR SELECT USING (true);

CREATE POLICY "Allow anon read nppa" ON public.nppa_ceiling_prices
    FOR SELECT USING (true);

-- Query logs: append-only for anonymous users, read own only
CREATE POLICY "Allow anon insert query_logs" ON public.query_logs
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anon read own query_logs" ON public.query_logs
    FOR SELECT USING (true);

-- =============================================================================
-- FUNCTIONS & VIEWS
-- =============================================================================

-- Function: find_nearest_stores(lat, lng, radius_km, limit)
-- Returns nearest Jan Aushadhi stores within radius (in km) using PostGIS
CREATE OR REPLACE FUNCTION public.find_nearest_stores(
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    radius_km DOUBLE PRECISION DEFAULT 10,
    store_limit INTEGER DEFAULT 5
)
RETURNS TABLE(
    store_code VARCHAR(50),
    name VARCHAR(500),
    address TEXT,
    city VARCHAR(200),
    district VARCHAR(200),
    state VARCHAR(200),
    pin_code VARCHAR(10),
    phone VARCHAR(20),
    distance_meters DOUBLE PRECISION
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.store_code,
        s.name,
        s.address,
        s.city,
        s.district,
        s.state,
        s.pin_code,
        s.phone,
        ST_Distance(s.location, ST_MakePoint(lng, lat)::geography) AS distance_meters
    FROM public.jan_aushadhi_stores s
    WHERE s.location IS NOT NULL
      AND ST_DWithin(
          s.location,
          ST_MakePoint(lng, lat)::geography,
          radius_km * 1000  -- convert km to meters
      )
    ORDER BY s.location <-> ST_MakePoint(lng, lat)::geography
    LIMIT store_limit;
END;
$$;

-- Function: find_stores_by_pin_with_prefix(pin, limit)
-- Returns stores at exact pin and neighboring pins (first 3 digits match)
CREATE OR REPLACE FUNCTION public.find_stores_by_pin_with_prefix(
    pin VARCHAR(10),
    store_limit INTEGER DEFAULT 5
)
RETURNS TABLE(
    store_code VARCHAR(50),
    name VARCHAR(500),
    address TEXT,
    city VARCHAR(200),
    district VARCHAR(200),
    state VARCHAR(200),
    pin_code VARCHAR(10),
    phone VARCHAR(20),
    match_type VARCHAR(10)  -- 'exact' or 'prefix'
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    -- Exact pin match first
    SELECT
        s.store_code,
        s.name,
        s.address,
        s.city,
        s.district,
        s.state,
        s.pin_code,
        s.phone,
        'exact'::VARCHAR AS match_type
    FROM public.jan_aushadhi_stores s
    WHERE s.pin_code = pin
    LIMIT store_limit;

    -- If less than limit found, add prefix matches
    IF (SELECT count(*) FROM public.jan_aushadhi_stores s WHERE s.pin_code = pin) < store_limit THEN
        RETURN QUERY
        SELECT
            s.store_code,
            s.name,
            s.address,
            s.city,
            s.district,
            s.state,
            s.pin_code,
            s.phone,
            'prefix'::VARCHAR AS match_type
        FROM public.jan_aushadhi_stores s
        WHERE s.pin_code LIKE (LEFT(pin, 3) || '%')
          AND s.pin_code != pin
        ORDER BY s.pin_code
        LIMIT store_limit;
    END IF;
END;
$$;

-- View: drug_with_generic_substitutes
-- Shows a drug with its cheapest generic alternatives (same salt+strength, cheaper)
CREATE OR REPLACE VIEW public.drug_with_generic_substitutes AS
SELECT
    d.id AS drug_id,
    d.brand_name,
    d.manufacturer,
    d.strength,
    d.dosage_form,
    d.mrp,
    d.pack_size,
    s.name AS salt_name,
    d.mrp AS reference_price,
    (
        SELECT json_agg(
            json_build_object(
                'brand_name', g.brand_name,
                'manufacturer', g.manufacturer,
                'mrp', g.mrp,
                'pack_size', g.pack_size,
                'savings', d.mrp - g.mrp,
                'savings_pct', ROUND(((d.mrp - g.mrp) / d.mrp * 100)::numeric, 1)
            )
            ORDER BY g.mrp
        )
        FROM public.drugs g
        WHERE g.salt_id = d.salt_id
          AND g.strength = d.strength
          AND g.mrp < d.mrp
          AND g.id != d.id
    ) AS cheaper_alternatives,
    (
        SELECT mrp FROM public.drugs g
        WHERE g.salt_id = d.salt_id
          AND g.strength = d.strength
          AND g.mrp < d.mrp
        ORDER BY g.mrp
        LIMIT 1
    ) AS cheapest_alternative_mrp,
    (
        SELECT ROUND(((d.mrp - min(g.mrp)) / d.mrp * 100)::numeric, 1)
        FROM public.drugs g
        WHERE g.salt_id = d.salt_id
          AND g.strength = d.strength
          AND g.mrp < d.mrp
    ) AS max_savings_pct
FROM public.drugs d
JOIN public.salts s ON d.salt_id = s.id;