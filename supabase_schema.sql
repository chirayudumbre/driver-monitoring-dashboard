-- ============================================================
-- AI Driver Monitoring System — Supabase Schema
-- Run this in Supabase SQL Editor (once)
-- ============================================================

-- Admin credentials table
CREATE TABLE IF NOT EXISTS admins (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,  -- SHA-256 hashed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    id                SERIAL PRIMARY KEY,
    vehicle_number    TEXT UNIQUE NOT NULL,
    vehicle_password  TEXT NOT NULL,  -- SHA-256 hashed
    vehicle_model     TEXT DEFAULT '',
    status            TEXT DEFAULT 'Active',
    registration_date DATE DEFAULT CURRENT_DATE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Drivers table
CREATE TABLE IF NOT EXISTS drivers (
    id              SERIAL PRIMARY KEY,
    driver_name     TEXT NOT NULL,
    username        TEXT UNIQUE NOT NULL,
    password        TEXT NOT NULL,  -- SHA-256 hashed
    phone_number    TEXT DEFAULT '',
    vehicle_id      TEXT REFERENCES vehicles(vehicle_number),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Alerts table (already exists, add severity if missing)
CREATE TABLE IF NOT EXISTS alerts (
    id           SERIAL PRIMARY KEY,
    vehicle_id   TEXT,
    driver_id    TEXT DEFAULT '',
    alert_type   TEXT NOT NULL,
    severity     TEXT DEFAULT 'Medium',
    snapshot_url TEXT DEFAULT '',
    timestamp    TIMESTAMPTZ DEFAULT NOW()
);

-- Active vehicle tracking (already exists)
CREATE TABLE IF NOT EXISTS active_vehicle (
    id         INTEGER PRIMARY KEY DEFAULT 1,
    vehicle_id TEXT DEFAULT 'UNKNOWN',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default row for active_vehicle if not exists
INSERT INTO active_vehicle (id, vehicle_id)
VALUES (1, 'UNKNOWN')
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- Row Level Security (RLS) — allow all for anon key
-- ============================================================
ALTER TABLE admins   ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE drivers  ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts   ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all" ON admins   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON vehicles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON drivers  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON alerts   FOR ALL USING (true) WITH CHECK (true);
