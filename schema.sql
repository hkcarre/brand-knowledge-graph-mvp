-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for semantic search (commented out if running on SQLite, uncomment for Postgres/Supabase)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Brands Table
CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    official_website VARCHAR(1024),
    description TEXT,
    logo_url VARCHAR(1024),
    is_claimed BOOLEAN DEFAULT FALSE,
    verification_status VARCHAR(50) DEFAULT 'unverified',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Creative Agencies
CREATE TABLE IF NOT EXISTS agencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    website VARCHAR(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Festivals / Award Bodies (e.g. Cannes Lions, D&AD, Clio)
CREATE TABLE IF NOT EXISTS festivals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    website VARCHAR(1024),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Festival Categories (e.g. Film, Digital, Pencil Categories)
CREATE TABLE IF NOT EXISTS festival_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    festival_id UUID REFERENCES festivals(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (festival_id, name)
);

-- 5. Campaigns / Creative Works
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    agency_id UUID REFERENCES agencies(id) ON DELETE SET NULL,
    title VARCHAR(512) NOT NULL,
    slug VARCHAR(512) NOT NULL,
    year INTEGER NOT NULL,
    description TEXT,
    case_study_url VARCHAR(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (brand_id, title, year)
);

-- 6. Award Winner Records
CREATE TABLE IF NOT EXISTS award_winners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    category_id UUID REFERENCES festival_categories(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    prize_level VARCHAR(100) NOT NULL, -- 'Grand Prix', 'Gold Lion', 'Black Pencil', 'Silver Clio'
    confidence_score DOUBLE PRECISION DEFAULT 1.0,
    source_url VARCHAR(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Provenance & Fact Verification
CREATE TABLE IF NOT EXISTS facts_provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL,            -- ID of the record (brand, product, or campaign)
    entity_table VARCHAR(100) NOT NULL, -- 'brands', 'campaigns', 'award_winners'
    source_url VARCHAR(1024) NOT NULL,
    source_type VARCHAR(100) NOT NULL,  -- 'brand_website', 'press_release', 'award_archive'
    extracted_text TEXT,
    confidence_score DOUBLE PRECISION NOT NULL,
    last_verified TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Crawler & Agent Traffic Logs (Observability)
CREATE TABLE IF NOT EXISTS crawler_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE SET NULL,
    crawler_name VARCHAR(100) NOT NULL, -- 'GPTBot', 'ClaudeBot', etc.
    ip_address VARCHAR(45) NOT NULL,
    request_path VARCHAR(2048) NOT NULL,
    user_agent TEXT NOT NULL,
    referrer TEXT,
    queried_keywords TEXT[],
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
