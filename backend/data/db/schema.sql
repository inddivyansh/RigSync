-- RigSync SQLite Schema
-- Created: 2026-10-17
-- Purpose: Store oil well fleet data with optimized indexes for time-series queries

-- Drop tables if exist (for clean rebuild)
DROP TABLE IF EXISTS maintenance_reports;
DROP TABLE IF EXISTS context_notes;
DROP TABLE IF EXISTS maintenance;
DROP TABLE IF EXISTS regulatory_events;
DROP TABLE IF EXISTS inspections;
DROP TABLE IF EXISTS equipment;
DROP TABLE IF EXISTS wells;
DROP TABLE IF EXISTS sop_rules;
DROP TABLE IF EXISTS well_types;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS areas;

-- Areas: Geographic blocks containing wells
CREATE TABLE areas (
    area_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    team_id TEXT NOT NULL,
    center_lat REAL,
    center_lon REAL
);

-- Teams: Organizational units managing areas
CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    lead_user_id TEXT
);

-- Users: Field operators, inspectors, technicians, supervisors
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    team_id TEXT NOT NULL
);

-- Well Types: Operating parameters and thresholds for well categories
CREATE TABLE well_types (
    well_type_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    production_threshold_c REAL NOT NULL,  -- Temperature difference threshold for "producing" status
    temp_alarm_c REAL NOT NULL,            -- Maximum wellhead temperature before alarm
    max_pressure_psi INTEGER NOT NULL      -- Maximum wellhead working pressure
);

-- SOP Rules: Extracted compliance rules from spill response and regulatory SOPs
CREATE TABLE sop_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id TEXT NOT NULL UNIQUE,      -- e.g., SR-01, RC-02
    category TEXT NOT NULL,                -- spill_response or regulatory_compliance
    description TEXT NOT NULL,
    deadline_hours INTEGER,                -- Reporting/action deadline in hours
    threshold_value REAL,                  -- Numeric threshold (e.g., 5 bbl for reportable spill)
    threshold_unit TEXT                    -- Unit for threshold (bbl, pct_tph, days)
);

-- Wells: Master list of oil well assets
CREATE TABLE wells (
    asset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_category TEXT DEFAULT 'oil_well',
    well_type TEXT NOT NULL,               -- FK to well_types(well_type_code)
    area_id TEXT NOT NULL,                 -- FK to areas(area_id)
    team_id TEXT NOT NULL,                 -- FK to teams(team_id)
    in_charge_user_id TEXT,                -- FK to users(user_id)
    lat REAL,
    lon REAL,
    installed_on TEXT,                     -- ISO date: YYYY-MM-DD
    recorded_status TEXT,                  -- Status from metadata: active, down, decommissioned
    FOREIGN KEY (area_id) REFERENCES areas(area_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (in_charge_user_id) REFERENCES users(user_id),
    FOREIGN KEY (well_type) REFERENCES well_types(well_type_code)
);

-- Equipment: Components installed on each well
CREATE TABLE equipment (
    equipment_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,               -- FK to wells(asset_id)
    kind TEXT NOT NULL,                    -- wellhead, pump_jack, rod_string, downhole_pump, flowline
    model TEXT,
    FOREIGN KEY (asset_id) REFERENCES wells(asset_id)
);

-- Inspections: Weekly drone/manual inspections with thermal readings
CREATE TABLE inspections (
    inspection_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,               -- FK to wells(asset_id)
    inspected_at TEXT NOT NULL,           -- ISO timestamp: YYYY-MM-DDTHH:MM:SSZ
    inspector_user_id TEXT NOT NULL,      -- FK to users(user_id)
    method TEXT,                          -- drone or manual
    ambient_temp_c REAL NOT NULL,
    wellhead_temp_c REAL NOT NULL,
    spill_detected INTEGER DEFAULT 0,     -- 0=false, 1=true
    spill_area_pct REAL,                  -- Percentage of pad area affected
    spill_est_volume_bbl REAL,            -- Estimated volume in barrels
    notes TEXT,                           -- Inspector observations
    evidence_images TEXT,                 -- JSON array of image paths (stored as TEXT)
    FOREIGN KEY (asset_id) REFERENCES wells(asset_id),
    FOREIGN KEY (inspector_user_id) REFERENCES users(user_id)
);

-- Regulatory Events: External agency interactions (NOVs, inspections, fines)
CREATE TABLE regulatory_events (
    event_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,               -- FK to wells(asset_id)
    event_type TEXT NOT NULL,             -- notice_of_violation, agency_inspection, fine, permit
    agency TEXT,                          -- State Oil & Gas Commission, EPA Regional Office
    event_date TEXT NOT NULL,             -- ISO date
    description TEXT,
    status TEXT DEFAULT 'open',           -- open or closed
    response_due_date TEXT,               -- ISO date
    nov_response_filed TEXT,              -- ISO date when response filed
    closure_date TEXT,                    -- ISO date when agency closed event
    FOREIGN KEY (asset_id) REFERENCES wells(asset_id)
);

-- Maintenance: Work orders for repairs, scheduled maintenance, and tests
CREATE TABLE maintenance (
    maintenance_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,               -- FK to wells(asset_id)
    started_at TEXT NOT NULL,             -- ISO timestamp
    completed_at TEXT,                    -- ISO timestamp
    maintenance_type TEXT NOT NULL,       -- scheduled, corrective, emergency
    equipment_kind TEXT,                  -- Which equipment was serviced
    issue TEXT NOT NULL,                  -- Description of issue or scheduled work
    action_taken TEXT,                    -- Summary of work performed
    technician_user_id TEXT,              -- FK to users(user_id)
    contractor TEXT,                      -- External contractor name (if any)
    downtime_hours INTEGER,               -- Well downtime for this maintenance
    cost_labor REAL,                      -- Labor cost in USD
    cost_parts REAL,                      -- Parts cost in USD
    cost_total REAL,                      -- Total cost in USD
    triggered_by_inspection_id TEXT,      -- FK to inspections(inspection_id) if inspection found issue
    report_file TEXT,                     -- Path to detailed markdown report (if exists)
    FOREIGN KEY (asset_id) REFERENCES wells(asset_id),
    FOREIGN KEY (technician_user_id) REFERENCES users(user_id),
    FOREIGN KEY (triggered_by_inspection_id) REFERENCES inspections(inspection_id)
);

-- Context Notes: Human annotations, corrections, and operator feedback
CREATE TABLE context_notes (
    note_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,               -- FK to wells(asset_id)
    created_at TEXT NOT NULL,             -- ISO timestamp
    author_user_id TEXT NOT NULL,         -- FK to users(user_id)
    note_type TEXT NOT NULL,              -- correction, operator_note, operator_feedback
    inspection_id TEXT,                   -- FK to inspections(inspection_id) if note references inspection
    text TEXT NOT NULL,                   -- Note content
    valid_from TEXT,                      -- ISO date: when this note starts applying
    valid_to TEXT,                        -- ISO date: when this note stops applying (NULL = still valid)
    FOREIGN KEY (asset_id) REFERENCES wells(asset_id),
    FOREIGN KEY (author_user_id) REFERENCES users(user_id),
    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id)
);

-- Maintenance Reports: Parsed structured data from detailed markdown reports
CREATE TABLE maintenance_reports (
    maintenance_id TEXT PRIMARY KEY,      -- FK to maintenance(maintenance_id)
    root_cause TEXT,                      -- Extracted from ## Root cause section
    compliance_json TEXT,                 -- JSON: [{protocol_id, result, detail}]
    parts_json TEXT,                      -- JSON: {labor, parts, total}
    report_path TEXT NOT NULL,            -- Relative path to markdown file
    FOREIGN KEY (maintenance_id) REFERENCES maintenance(maintenance_id)
);

-- Indexes for time-series queries (critical for performance)
CREATE INDEX idx_inspections_asset_date ON inspections(asset_id, inspected_at);
CREATE INDEX idx_maintenance_asset_date ON maintenance(asset_id, started_at);
CREATE INDEX idx_context_asset_valid ON context_notes(asset_id, valid_from, valid_to);
CREATE INDEX idx_inspections_date ON inspections(inspected_at);
CREATE INDEX idx_maintenance_type ON maintenance(maintenance_type, equipment_kind);
CREATE INDEX idx_wells_area ON wells(area_id, well_type);
CREATE INDEX idx_regulatory_status ON regulatory_events(status, event_date);

-- Insert metadata
CREATE TABLE schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT INTO schema_metadata (key, value) VALUES 
    ('schema_version', '1.0.0'),
    ('created_at', datetime('now')),
    ('description', 'RigSync Asset Intelligence Database');
