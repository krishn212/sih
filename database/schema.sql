-- Legal Metrology Compliance Scanner — Production Schema
-- Run this in Supabase SQL Editor (Project → SQL Editor → New Query → Paste → Run)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Types ──────────────────────────────────────────────────────────────────
DO $$ BEGIN
  CREATE TYPE role_type AS ENUM ('INSPECTOR', 'ADMIN');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE calibration_tier AS ENUM ('ARUCO', 'ID_CARD', 'COIN', 'NONE');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE status_type AS ENUM ('PASS', 'FAIL', 'MANUAL_REVIEW');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ─── Tables ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role role_type DEFAULT 'INSPECTOR',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    barcode TEXT UNIQUE,
    brand_name TEXT NOT NULL,
    manufacturer_details TEXT,
    category TEXT NOT NULL,
    surface_type TEXT CHECK (surface_type IN ('FLAT', 'CURVED')) DEFAULT 'FLAT'
);

CREATE TABLE IF NOT EXISTS rule_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_code TEXT NOT NULL,
    source_clause TEXT NOT NULL,
    applies_to TEXT,
    condition TEXT NOT NULL,
    threshold TEXT,
    effective_from DATE NOT NULL,
    effective_until DATE,
    severity TEXT,
    verified BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    image_url TEXT NOT NULL,
    calibration_used calibration_tier NOT NULL,
    px_per_mm_ratio NUMERIC(10, 4),
    overall_status status_type NOT NULL,
    deployment_mode TEXT DEFAULT 'HANDHELD',
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    rule_version_id UUID REFERENCES rule_versions(id),
    field_name TEXT NOT NULL,
    expected_value TEXT,
    detected_value TEXT,
    measured_height_mm NUMERIC(5, 2),
    required_height_mm NUMERIC(5, 2),
    status status_type NOT NULL,
    confidence_score NUMERIC(4, 3),
    evidence_crop_url TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    violation_id UUID REFERENCES violations(id) ON DELETE CASCADE,
    admin_id UUID REFERENCES users(id),
    action_taken TEXT NOT NULL,
    override_reason TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    pdf_url TEXT,
    docx_url TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_scans_user     ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_scans_status   ON scans(overall_status);
CREATE INDEX IF NOT EXISTS idx_scans_date     ON scans(scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_violations_scan ON violations(scan_id);
CREATE INDEX IF NOT EXISTS idx_violations_status ON violations(status);
