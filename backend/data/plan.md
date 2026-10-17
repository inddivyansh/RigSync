# RigSync Implementation Plan

**Project:** Agentic RAG-powered Asset Intelligence Copilot for Oil Wells  
**Planning Date:** 2026-10-17  
**Planner:** Workflow Planning Agent  
**Today's Date for Business Rules:** 2026-10-16

## Business Rules Extracted from Documents

### Production Status Calculation
- **T200 wells:** Producing if `(wellhead_temp_c - ambient_temp_c) >= 15°C` (from T200.md §9.3)
- **T350 wells:** Producing if `(wellhead_temp_c - ambient_temp_c) >= 20°C` (from T350.md §3)

### Downtime Calculation
- Each non-producing weekly inspection = **7 days downtime**
- Missed inspections (gaps >14 days) = **0 downtime** for missing weeks

### Spill Response Deadlines (from spill-response-sop.md)
- **SR-01:** Reportable spills (≥5 bbl) require written notice within **24 hours** of discovery; Major spills (≥25 bbl) within **2 hours**
- **SR-02:** Source must be stopped and spill contained within **4 hours** of discovery
- **SR-03:** Contaminated soil cleaned to **≤1.0% TPH**; Reportable spills require agency verification within **60 days**
- **SR-04:** All spills (including minor) must be recorded with volume and affected area

### Regulatory Compliance (from regulatory-compliance-sop.md)
- **RC-01:** Wells must be inspected at least once every **14 days**
- **RC-02:** Flowlines must pass integrity test once per **calendar year**
- **RC-03:** Wells down for more than **14 consecutive days** must be reported to area supervisor
- **RC-04:** NOV responses must be filed within **30 days**
- **RC-05:** Flowline maintenance program: weekly visual inspections, prompt leak repair

### Temperature Alarms
- **T200:** Wellhead must stay **≤85°C** (above requires shut-in and inspection within 24h)
- **T350:** Wellhead must stay **≤95°C**

### Maintenance Escalation (from T200.md §10)
- **3 or more corrective events** on same equipment kind in 12 months → requires RCA before next repair closes
- **Downtime >14 consecutive days** → report to area production supervisor

---

## Implementation Phases

This plan follows a dependency-ordered sequence: data foundation → semantic layer → business logic → agent orchestration → API layer.

---

## Phase 1: Data Ingestion Foundation (FEAT-001)

### Overview
Create SQLite schema and load all fleet metadata, well data, and maintenance reports. Extract business rules from manuals and SOPs into structured JSON.

- [ ] **1. Design SQLite schema**
      
      **What:** Create `backend/data/db/schema.sql` with 11 tables for normalized relational data:
      - `wells` (asset_id PK, name, well_type, area_id, team_id, in_charge_user_id, lat, lon, installed_on, recorded_status)
      - `equipment` (equipment_id PK, asset_id FK, kind, model)
      - `inspections` (inspection_id PK, asset_id FK, inspected_at, inspector_user_id, method, ambient_temp_c, wellhead_temp_c, spill_detected, spill_area_pct, spill_est_volume_bbl, notes)
      - `maintenance` (maintenance_id PK, asset_id FK, started_at, completed_at, maintenance_type, equipment_kind, issue, action_taken, technician_user_id, contractor, downtime_hours, cost_labor, cost_parts, cost_total, triggered_by_inspection_id, report_file)
      - `context_notes` (note_id PK, asset_id FK, created_at, author_user_id, note_type, inspection_id, text, valid_from, valid_to)
      - `maintenance_reports` (maintenance_id PK FK, root_cause, compliance_json, parts_json, report_path)
      - `areas` (area_id PK, name, team_id, center_lat, center_lon)
      - `teams` (team_id PK, name, lead_user_id)
      - `users` (user_id PK, name, role, team_id)
      - `well_types` (well_type_code PK, name, production_threshold_c, temp_alarm_c, max_pressure_psi)
      - `sop_rules` (rule_id PK, protocol_id, category, description, deadline_hours, threshold_value, threshold_unit)
      
      Add indexes for time-series queries:
      - `idx_inspections_asset_date` on `inspections(asset_id, inspected_at)`
      - `idx_maintenance_asset_date` on `maintenance(asset_id, started_at)`
      - `idx_context_asset` on `context_notes(asset_id, valid_from, valid_to)`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\data\db\schema.sql`
      
      **Verify:** `sqlite3 data/db/oilwells.db < data/db/schema.sql && sqlite3 data/db/oilwells.db ".schema"` — expect 11 CREATE TABLE statements with indexes

- [ ] **2. Write fleet metadata ingestion script**
      
      **What:** Create `backend/scripts/ingest_fleet.py`:
      - Parse `sample-data/fleet/areas.json` to populate `areas`, `teams`, `users` tables
      - Parse `sample-data/fleet/well-types/T200.md` to extract:
        - Production threshold from §9.3: "**15 °C above ambient**" → 15
        - Temp alarm from §9.4: "**at or below 85 °C**" → 85
        - Max pressure from §9.1: "**3,000 psi**" → 3000
      - Parse `sample-data/fleet/well-types/T350.md` to extract:
        - Production threshold from §3: "**20 °C above ambient**" → 20
        - Temp alarm from §4: "**at or below 95 °C**" → 95
        - Max pressure (table in §2): "**5,000 psi**" → 5000
      - Use regex `(\d+)\s*°?C` and `(\d+[,\d]*)\s*psi` to extract numeric values
      - Insert into `well_types` table with well_type_code='T200' and 'T350'
      - Log each extraction with source file and line number for audit
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\ingest_fleet.py`
      
      **Verify:** `python backend/scripts/ingest_fleet.py && sqlite3 data/db/oilwells.db "SELECT * FROM well_types;"` — expect 2 rows: T200 (15, 85, 3000), T350 (20, 95, 5000)

- [ ] **3. Write SOP rules parser**
      
      **What:** Create `backend/scripts/parse_sops.py`:
      - Parse `sample-data/fleet/sops/spill-response-sop.md`:
        - SR-01: Extract "**24 hours**" from "within **24 hours** of discovery" → deadline_hours=24 for reportable (≥5 bbl)
        - SR-01: Extract "**2 hours**" for major spills (≥25 bbl) → deadline_hours=2
        - SR-02: Extract "**4 hours**" from contain requirement → deadline_hours=4
        - SR-03: Extract "**60 days**" from verification deadline → deadline_hours=1440
        - SR-03: Extract "**1.0% TPH**" as threshold_value=1.0, threshold_unit='pct_tph'
      - Parse `sample-data/fleet/sops/regulatory-compliance-sop.md`:
        - RC-01: Extract "**14 days**" from inspection requirement → deadline_hours=336
        - RC-02: Extract "**once per calendar year**" → deadline_hours=8760
        - RC-03: Extract "**14 consecutive days**" downtime reporting → deadline_hours=336
        - RC-04: Extract "**30 days**" NOV response → deadline_hours=720
      - Write to `data/rules/rules.json` as array of objects: `[{protocol_id, category, description, deadline_hours, threshold_value, threshold_unit}, ...]`
      - Use regex `\*\*(\d+)\s+(hours?|days?)\*\*` to extract deadlines
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\parse_sops.py`, `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\data\rules\rules.json` (generated)
      
      **Verify:** `python backend/scripts/parse_sops.py && cat data/rules/rules.json | jq 'length'` — expect 9 rules; `jq '.[] | select(.protocol_id=="SR-01")'` — expect deadline_hours=24 and 2

- [ ] **4. Write per-well data ingestion script**
      
      **What:** Create `backend/scripts/ingest_wells.py`:
      - Scan `sample-data/assets/` for directories WELL-0001 to WELL-0200 (200 wells)
      - For each well directory:
        - Parse `metadata.json` → insert into `wells` table (asset_id, name, well_type, area_id, team_id, in_charge_user_id, lat=location.lat, lon=location.lon, installed_on, recorded_status)
        - Parse `metadata.json` equipment array → insert into `equipment` table (equipment_id, asset_id, kind, model)
        - Parse `inspections.jsonl` (JSONL with ~203 lines for WELL-0001) → insert into `inspections` table using `pandas.read_json(lines=True)`
        - Parse `maintenance.jsonl` (~32 lines for WELL-0001) → insert into `maintenance` table
        - Parse `context.jsonl` (~3 lines for WELL-0001) → insert into `context_notes` table
      - Handle null fields: spill_area_pct and spill_est_volume_bbl are null when spill_detected=false
      - Commit in batches of 50 wells for performance
      - Log progress: "Ingested WELL-XXXX: N inspections, M maintenance, K context notes"
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\ingest_wells.py`
      
      **Verify:** `python backend/scripts/ingest_wells.py && sqlite3 data/db/oilwells.db "SELECT COUNT(*) FROM wells; SELECT COUNT(*) FROM inspections; SELECT COUNT(*) FROM maintenance;"` — expect ~200, ~40000, ~5700

- [ ] **5. Write maintenance reports parser**
      
      **What:** Create `backend/scripts/ingest_reports.py`:
      - For each well directory in `sample-data/assets/`, scan `maintenance-reports/` subdirectory
      - Parse `*.md` files (e.g., `MNT-0001-002.md`):
        - Extract maintenance_id from filename using regex `MNT-(\d{4}-\d{3})`
        - Extract root_cause from section `## Root cause` (next non-empty line after header)
        - Extract compliance table from section `## Compliance check`:
          - Parse markdown table with columns: Protocol, Result, Detail
          - Convert to JSON: `[{protocol_id: "WS-01", result: "Met", detail: "..."}, ...]`
        - Extract parts cost from section `## Parts and cost`:
          - Parse markdown table, extract Total row value
          - Store as JSON: `{labor: 2737, parts: 3191, total: 5928}`
        - Insert into `maintenance_reports` table (maintenance_id FK to maintenance, root_cause, compliance_json, parts_json, report_path)
      - Use regex to extract markdown sections: `## (.*?)\n(.*?)(?=\n##|\Z)` with DOTALL flag
      - Handle reports without some sections (e.g., older reports may lack compliance table)
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\ingest_reports.py`
      
      **Verify:** `python backend/scripts/ingest_reports.py && sqlite3 data/db/oilwells.db "SELECT COUNT(*) FROM maintenance_reports; SELECT root_cause FROM maintenance_reports WHERE maintenance_id='MNT-0001-002';"` — expect ~1500 rows, root_cause='Thread fatigue from pump jack vibration'

---

## Phase 2: Semantic Search & Knowledge Graph (FEAT-002)

### Overview
Build ChromaDB vector embeddings for semantic search and NetworkX graph for relationship traversal. Independent of Phase 1 but uses its SQLite data.

- [ ] **6. Create vector embeddings for manuals and SOPs**
      
      **What:** Create `backend/scripts/build_embeddings.py`:
      - Initialize ChromaDB persistent client at `data/chroma/`
      - Create collection `manuals` with embedding function `sentence-transformers/all-MiniLM-L6-v2` (384 dims)
      - Parse `sample-data/fleet/well-types/T200.md` and `T350.md`:
        - Split by section headers: regex `## (\d+\.?\d*)\s+(.*?)\n(.*?)(?=\n##|\Z)` → extract (section_number, section_title, section_text)
        - Generate embedding for each section_text
        - Add to collection with metadata: `{source_file: 'T200.md', well_type_code: 'T200', section_number: '9.3', section_title: 'Production temperature rule', doc_type: 'manual'}`
        - Document ID format: `manual_T200_s9.3`
      - Create collection `sops` similarly for spill-response-sop.md and regulatory-compliance-sop.md:
        - Split by protocol ID: regex `\*\*(SR-\d+|RC-\d+)\*\*` marks protocol boundaries
        - Metadata: `{source_file: 'spill-response-sop.md', protocol_id: 'SR-01', doc_type: 'sop'}`
      - Log: "Created embeddings: T200 (N sections), T350 (M sections), Spill SOP (X protocols), Compliance SOP (Y protocols)"
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\build_embeddings.py` (partial — manuals/SOPs only)
      
      **Verify:** `python backend/scripts/build_embeddings.py && python -c "import chromadb; client = chromadb.PersistentClient(path='data/chroma'); print(client.get_collection('manuals').count())"` — expect ~30 chunks

- [ ] **7. Create vector embeddings for maintenance reports and context notes**
      
      **What:** Extend `build_embeddings.py`:
      - Create collection `reports`:
        - Query `maintenance_reports` table for all report_path values
        - Read each markdown file from `sample-data/assets/{well}/maintenance-reports/{file}`
        - Store entire report as single document (reports are 200-400 words, fit in embedding context)
        - Metadata: `{source_file: report_path, asset_id: extract from path, maintenance_id: from filename, doc_type: 'report', root_cause: from maintenance_reports table}`
        - Document ID: `report_{maintenance_id}`
      - Create collection `context`:
        - Query `context_notes` table for all notes
        - Combine fields into searchable text: `f"{note_type}: {text} (by {author_user_id} on {created_at})"`
        - Metadata: `{asset_id, note_id, note_type, author_user_id, created_at, valid_from, valid_to, doc_type: 'context'}`
        - Document ID: `context_{note_id}`
      - Log: "Indexed reports (N documents), context notes (M documents)"
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\build_embeddings.py` (complete)
      
      **Verify:** `python -c "import chromadb; client = chromadb.PersistentClient(path='data/chroma'); print(client.get_collection('reports').count(), client.get_collection('context').count())"` — expect ~1500, ~600

- [ ] **8. Build NetworkX knowledge graph**
      
      **What:** Create `backend/scripts/build_knowledge_graph.py`:
      - Create directed graph with node types: Well, Area, Team, User, Equipment
      - Query SQLite to populate nodes:
        - Wells: `SELECT asset_id, name, well_type, lat, lon, recorded_status FROM wells`
        - Areas: `SELECT area_id, name, center_lat, center_lon FROM areas`
        - Teams: `SELECT team_id, name, lead_user_id FROM teams`
        - Users: `SELECT user_id, name, role, team_id FROM users`
        - Equipment: `SELECT equipment_id, asset_id, kind, model FROM equipment`
      - Add edges:
        - Well → Area: (asset_id, area_id, relation='belongs_to')
        - Area → Team: (area_id, team_id, relation='managed_by')
        - Team → User: (team_id, user_id, relation='has_member') for all users in team
        - User → Team: (user_id, team_id, relation='leads') for team leads only
        - Well → User: (asset_id, user_id, relation='in_charge')
        - Well → Equipment: (asset_id, equipment_id, relation='has_component')
        - Equipment → Equipment: chain for wellhead → pump_jack → rod_string → downhole_pump → flowline (relation='connected_to')
      - Export to JSON using `networkx.node_link_data()` → `data/graph/knowledge_graph.json`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\build_knowledge_graph.py` (partial — graph construction)
      
      **Verify:** `python backend/scripts/build_knowledge_graph.py && python -c "import json; g = json.load(open('data/graph/knowledge_graph.json')); print(f'Nodes: {len(g[\"nodes\"])}, Edges: {len(g[\"links\"])}')"` — expect ~2500 nodes, ~5000 edges

- [ ] **9. Add precomputed graph indexes**
      
      **What:** Extend `build_knowledge_graph.py`:
      - Compute `well_hierarchy` for each well: traverse Well → Area → Team → User (in_charge + team lead) → Equipment list
        - Store as dict: `{asset_id: {area, area_name, team, team_name, team_lead, in_charge_user, equipment: [{equipment_id, kind, model}]}}`
      - Compute `area_wells`: for each area, collect all asset_ids via Well → Area edges
        - Store as dict: `{area_id: [asset_id1, asset_id2, ...]}`
      - Compute `user_wells`: for each user, collect wells they're in_charge of
        - Store as dict: `{user_id: [asset_id1, asset_id2, ...]}`
      - Add to JSON export: `{nodes: [...], links: [...], indexes: {well_hierarchy, area_wells, user_wells}}`
      - Log: "Precomputed indexes: 200 well hierarchies, 4 area lists, 15 user lists"
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\build_knowledge_graph.py` (complete)
      
      **Verify:** `python -c "import json; g = json.load(open('data/graph/knowledge_graph.json')); idx = g['indexes']; print(f'Hierarchies: {len(idx[\"well_hierarchy\"])}, Areas: {len(idx[\"area_wells\"])}, Users: {len(idx[\"user_wells\"])}')"` — expect 200, 4, ~15

---

## Phase 3: Agent Tools Implementation (FEAT-003)

### Overview
Create 8 specialized tools that the agent will orchestrate. Each tool is a Python class with Pydantic schema for LLM function calling. Depends on Phases 1 & 2.

- [ ] **10. Implement SQL query tool with safety checks**
      
      **What:** Create `backend/tools/sql_query.py`:
      - Class `SQLQueryTool` with method `execute(query: str, params: dict) → dict`
      - Connect to `data/db/oilwells.db` using sqlite3
      - Validate query: whitelist SELECT, WHERE, JOIN, GROUP BY, ORDER BY, LIMIT, HAVING
      - Block DML/DDL: raise error if query contains INSERT, UPDATE, DELETE, DROP, ALTER, CREATE
      - Use parameterized queries: `cursor.execute(query, params)` to prevent SQL injection
      - Return `{columns: [col_names], rows: [[val1, val2], ...], row_count: int}`
      - Add helper method `apply_production_threshold(df, well_type)` to compute is_producing column: `df['is_producing'] = (df['wellhead_temp_c'] - df['ambient_temp_c']) >= threshold`
      - Load well_types table on initialization to cache production thresholds (T200=15, T350=20)
      - Pydantic schema for LLM: `{name: 'sql_query', description: 'Execute SQL query on oilwells database', parameters: {query: str, params: dict}}`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\tools\sql_query.py`
      
      **Verify:** `python -c "from tools.sql_query import SQLQueryTool; tool = SQLQueryTool(); result = tool.execute('SELECT COUNT(*) as cnt FROM wells', {}); print(result)"` — expect {columns: ['cnt'], rows: [[200]], row_count: 1}

- [ ] **11. Implement vector search tool with citation formatting**
      
      **What:** Create `backend/tools/vector_search.py`:
      - Class `VectorSearchTool` with method `search(query_text: str, collection_name: str, filter_metadata: dict, n_results: int) → list[dict]`
      - Initialize ChromaDB client: `chromadb.PersistentClient(path='data/chroma')`
      - Validate collection_name in ['manuals', 'sops', 'reports', 'context']
      - Call `collection.query(query_texts=[query_text], where=filter_metadata, n_results=n_results)`
      - Return list of dicts: `[{document: str, metadata: dict, distance: float, citation: str}]`
      - Generate citation string from metadata:
        - manual: `f"{metadata['well_type_code']} Manual §{metadata['section_number']}"`
        - sop: `f"SOP-{metadata['protocol_id'][:2]} §{metadata['protocol_id']}"`
        - report: `f"{metadata['maintenance_id']} Report"`
        - context: `f"Note by {metadata['author_user_id']} on {metadata['created_at'][:10]}"`
      - Pydantic schema: `{name: 'vector_search', description: 'Semantic search in manuals, SOPs, reports, context notes', parameters: {query_text: str, collection_name: str, filter_metadata: dict, n_results: int}}`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\tools\vector_search.py`
      
      **Verify:** `python -c "from tools.vector_search import VectorSearchTool; tool = VectorSearchTool(); result = tool.search('production temperature rule', 'manuals', {}, 1); print(result[0]['citation'])"` — expect 'T200 Manual §9.3' or 'T350 Manual §3'

- [ ] **12. Implement graph traversal tool**
      
      **What:** Create `backend/tools/graph_query.py`:
      - Class `GraphQueryTool` with methods:
        - `get_well_hierarchy(asset_id: str) → dict` — use precomputed index from knowledge_graph.json
        - `get_area_wells(area_id: str) → list[str]` — use precomputed index
        - `get_neighbors(node_id: str, relation: str) → list[dict]` — traverse graph edges matching relation
        - `traverse(start_node: str, relation_path: list[str], max_depth: int) → list[dict]` — follow edge sequence
      - Load graph on initialization: `import json; self.graph_data = json.load(open('data/graph/knowledge_graph.json')); self.indexes = self.graph_data['indexes']`
      - Reconstruct NetworkX graph from JSON: `self.graph = networkx.node_link_graph(self.graph_data)`
      - Pydantic schema: `{name: 'graph_query', description: 'Query well-area-team-user-equipment relationships', parameters: {operation: str, node_id: str, ...}}`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\tools\graph_query.py`
      
      **Verify:** `python -c "from tools.graph_query import GraphQueryTool; tool = GraphQueryTool(); hierarchy = tool.get_well_hierarchy('WELL-0001'); print(hierarchy['area'], hierarchy['team'])"` — expect 'SW-23', 'TEAM-SW'

- [ ] **13. Implement downtime calculator with production rules**
      
      **What:** Create `backend/tools/downtime_calc.py`:
      - Class `DowntimeCalculatorTool` with method `calculate_downtime(asset_id: str, start_date: str, end_date: str) → dict`
      - Query inspections table: `SELECT * FROM inspections WHERE asset_id = ? AND inspected_at BETWEEN ? AND ? ORDER BY inspected_at`
      - Query well metadata: `SELECT well_type FROM wells WHERE asset_id = ?`
      - Load production threshold from well_types table for that well_type
      - For each inspection:
        - Compute temp_diff = wellhead_temp_c - ambient_temp_c
        - is_producing = (temp_diff >= threshold)
        - If not producing, add 7 days downtime
      - Detect missed inspections: if gap between consecutive inspections > 14 days, count 0 downtime for missing weeks
      - Query context_notes for planned shutdowns: `SELECT * FROM context_notes WHERE asset_id = ? AND note_type IN ('operator_note', 'operator_feedback') AND valid_from <= ? AND (valid_to IS NULL OR valid_to >= ?)`
      - Annotate non-producing weeks with reason from context notes if available
      - Return: `{total_downtime_days: int, producing_weeks: int, non_producing_weeks: int, missed_weeks: int, details: [{inspection_id, date, is_producing, temp_diff, threshold, reason}]}`
      - Pydantic schema: `{name: 'downtime_calc', description: 'Calculate well downtime using production temperature threshold', parameters: {asset_id: str, start_date: str, end_date: str}}`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\tools\downtime_calc.py`
      
      **Verify:** `python -c "from tools.downtime_calc import DowntimeCalculatorTool; tool = DowntimeCalculatorTool(); result = tool.calculate_downtime('WELL-0001', '2026-10-01', '2026-10-16'); print(f'{result[\"non_producing_weeks\"]} weeks, {result[\"total_downtime_days\"]} days')"` — expect 2 weeks, 14 days (Oct 8 and Oct 15 inspections not producing per context note about planned shutdown)

- [ ] **14. Implement compliance checker for SOP rules**
      
      **What:** Create `backend/tools/compliance_check.py`:
      - Class `ComplianceCheckTool` with method `check_violations(asset_id: str, start_date: str, end_date: str) → list[dict]`
      - Load rules from `data/rules/rules.json`
      - For each rule, implement check logic:
        - **RC-01** (inspect every 14 days): Query inspections, find gaps > 14 days → violation
        - **RC-02** (flowline test annually): Query maintenance for issue='Annual flowline integrity test', check if exists in each calendar year → violation if missing
        - **RC-03** (report downtime >14 days): Use downtime_calc to find consecutive downtime, check if > 336 hours
        - **SR-01** (reportable spill report within 24h): Query inspections for spills ≥5 bbl, check maintenance.started_at - inspection.inspected_at <= 24h
        - **SR-02** (contain within 4h): Check maintenance.started_at - inspection.inspected_at <= 4h for spills
        - **SR-03** (verify within 60 days): Check if maintenance_reports.compliance_json contains agency verification within 60 days of spill
      - Return: `[{rule_id: str, protocol_id: str, violated: bool, violation_date: str, details: str, deadline_missed_by_hours: int}]`
      - Pydantic schema: `{name: 'compliance_check', description: 'Check SOP rule violations for a well', parameters: {asset_id: str, start_date: str, end_date: str}}`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\tools\compliance_check.py`
      
      **Verify:** `python -c "from tools.compliance_check import ComplianceCheckTool; tool = ComplianceCheckTool(); violations = tool.check_violations('WELL-0001', '2023-01-01', '2023-12-31'); print([v['protocol_id'] for v in violations if v['violated']])"` — expect list of violated protocol IDs (e.g., ['SR-02'] for MNT-0001-002 which was contained 5.3h late per report)

- [ ] **15. Implement memory retrieval tool**
      
      **What:** Create `backend/tools/memory_retrieval.py`:
      - Class `MemoryRetrievalTool` with method `get_context(user_id: str, asset_id: str, scope: str) → dict`
      - Read from `data/memory/` directory:
        - `user_{user_id}.json` — user-scoped corrections private to that user
        - `well_{asset_id}.json` — well-scoped corrections visible to all users for that well
        - `global_rules.json` — team-wide overrides (e.g., "T350 wells need RCA after 2 repairs, not 3")
      - Correction format: `{correction_id, created_at, author_user_id, scope, entity_id, field, old_value, new_value, reason, valid_from, valid_to}`
      - Filter by scope parameter: 'user' (return only user-scoped), 'well' (return well-scoped), 'global' (return global), 'all' (return all applicable)
      - Also read conversation history from `user_{user_id}_history.jsonl` (last 10 messages)
      - Return: `{corrections: list[dict], conversation_history: list[dict]}`
      - Pydantic schema: `{name: 'memory_retrieval', description: 'Fetch corrections and conversation history', parameters: {user_id: str, asset_id: str, scope: str}}`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\tools\memory_retrieval.py`
      
      **Verify:** Create test file `data/memory/well_WELL-0001.json` with `[{correction_id: 'COR-001', field: 'wellhead_temp_c', old_value: 24.0, new_value: 41.0}]`, then run `python -c "from tools.memory_retrieval import MemoryRetrievalTool; tool = MemoryRetrievalTool(); ctx = tool.get_context('U-101', 'WELL-0001', 'well'); print(len(ctx['corrections']))"` — expect 1

- [ ] **16. Implement memory update tool with provenance**
      
      **What:** Create `backend/tools/memory_update.py`:
      - Class `MemoryUpdateTool` with method `record_correction(user_id: str, asset_id: str, field: str, old_value: any, new_value: any, reason: str, scope: str) → dict`
      - Generate unique ID: `correction_id = f"COR-{int(time.time())}-{random.randint(1000,9999)}"`
      - Create correction object: `{correction_id, created_at: datetime.now().isoformat(), author_user_id: user_id, scope, entity_id: asset_id or 'global', field, old_value, new_value, reason, valid_from: datetime.now().isoformat(), valid_to: null}`
      - Append to appropriate JSON file based on scope:
        - 'user' → `data/memory/user_{user_id}.json`
        - 'well' → `data/memory/well_{asset_id}.json`
        - 'global' → `data/memory/global_rules.json`
      - Create directory and file if not exists
      - Load existing corrections, append new one, write back
      - Trigger conflict detection internally: call `ConflictDetectTool.detect_conflicts(asset_id, field, new_value)`
      - Return: `{correction_id, status: 'recorded', conflicts: list[dict] | null}`
      - Pydantic schema: `{name: 'memory_update', description: 'Record a data correction with full provenance', parameters: {user_id: str, asset_id: str, field: str, old_value: any, new_value: any, reason: str, scope: str}}`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\tools\memory_update.py`
      
      **Verify:** `python -c "from tools.memory_update import MemoryUpdateTool; tool = MemoryUpdateTool(); result = tool.record_correction('U-101', 'WELL-0164', 'wellhead_temp_c', 24.0, 41.0, 'Faulty thermal gun', 'well'); print(result['correction_id'])"` — expect 'COR-XXXXXXXXXX-XXXX' format

- [ ] **17. Implement conflict detector**
      
      **What:** Create `backend/tools/conflict_detect.py`:
      - Class `ConflictDetectTool` with method `detect_conflicts(asset_id: str, field: str, new_value: any) → list[dict]`
      - Compare new_value against 3 sources:
        1. **Latest SQLite data:** Query inspections/maintenance for most recent value of field for asset_id
        2. **Existing corrections:** Query memory JSON files for other corrections on same field
        3. **Context notes:** Query context_notes for observations that contradict new_value (e.g., "pump not moving" contradicts temp increase)
      - Assign severity:
        - 'high' if contradicts inspector observation from inspections table notes field
        - 'medium' if contradicts operator note from context_notes
        - 'low' if just different correction by another user in memory
      - Return: `[{conflict_type: str, source: str, source_id: str, existing_value: any, new_value: any, severity: str, details: str}]`
      - Pydantic schema: `{name: 'conflict_detect', description: 'Find conflicts between new value and existing data', parameters: {asset_id: str, field: str, new_value: any}}`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\tools\conflict_detect.py`
      
      **Verify:** For WELL-0164 with inspection note "Pump jack not moving": `python -c "from tools.conflict_detect import ConflictDetectTool; tool = ConflictDetectTool(); conflicts = tool.detect_conflicts('WELL-0164', 'wellhead_temp_c', 41.0); print(conflicts[0]['severity'])"` — expect 'high' due to pump observation conflict

---

## Phase 4: Agent Orchestration Layer (FEAT-004)

### Overview
Create LangGraph state machine for agentic reasoning, tool selection, and response synthesis. Depends on Phase 3 (tools must exist).

- [ ] **18. Define agent schemas**
      
      **What:** Create `backend/agent/schemas.py` with Pydantic models:
      - `QueryAnalysis`: intent (str from enum: status_check, trend_analysis, compliance_audit, downtime_report, correction_request, multi_well_comparison), entities (list[str]: well IDs, area names, dates), temporal_scope (str: date range), requires_tools (list[str]: tool names needed)
      - `ToolCall`: tool_name (str), parameters (dict), reasoning (str: why this tool)
      - `AgentResponse`: answer (str), citations (list[str]), visualization_type (str from enum: status_card, table, line_chart, bar_chart, map, heatmap), visualization_data (dict), confidence (float 0-1)
      - `MemoryCorrection`: user_id, asset_id, field, old_value, new_value, reason, scope
      - `ConflictAlert`: conflict_type, source, existing_value, new_value, severity (high/medium/low), recommendation (str: how to resolve)
      - All models use `model_config = ConfigDict(extra='forbid')` to validate strictly
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\agent\schemas.py`
      
      **Verify:** `python -c "from agent.schemas import QueryAnalysis; qa = QueryAnalysis(intent='status_check', entities=['WELL-0001'], temporal_scope='2026-10-15', requires_tools=['sql_query']); print(qa.intent)"` — expect 'status_check'

- [ ] **19. Write agent system prompt**
      
      **What:** Create `backend/agent/prompts.py` with system_prompt string:
      - Role: "You are RigSync, an asset intelligence copilot for oil field operations. You have access to 200 wells with 4 years of inspection, maintenance, and compliance data."
      - Query analysis instructions: "Determine intent (status_check, trend_analysis, compliance_audit, downtime_report, correction_request, multi_well_comparison). Extract entities (well IDs format WELL-XXXX, area names SW-23/SW-24/NE-07/NE-08, user IDs U-XXX, dates). Identify temporal scope (default: last 30 days if not specified)."
      - Tool selection rules: "Use sql_query for structured data (inspections, maintenance, equipment). Use vector_search for finding relevant manual sections, SOP protocols, or maintenance reports. Use graph_query for relationships (wells in area, team members, equipment hierarchy). Use downtime_calc when query asks about production, downtime, or well activity. Use compliance_check for SOP violations, deadlines, reporting requirements. Use memory_retrieval to check for corrections before answering. Use memory_update when user provides correction. Always use conflict_detect after memory_update."
      - Tool chaining examples:
        - "Which wells in SW-23 are not producing?" → graph_query(get_area_wells, 'SW-23') → sql_query(latest inspections for those wells) → downtime_calc(check production status) → synthesize answer
        - "User corrects WELL-0164 temp to 41.0°C" → memory_retrieval(check existing corrections) → memory_update(record correction) → conflict_detect(check for contradictions) → explain conflicts to user
      - Citation requirement: "Always cite sources using format [INS-0001-0203], [MNT-0001-002 Report], [T200 Manual §9.3], [SOP-SR §SR-01]. Track every data point used in answer."
      - Add 10 few-shot examples mapping query → tool sequence
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\agent\prompts.py`
      
      **Verify:** `python -c "from agent.prompts import system_prompt; print(len(system_prompt))"` — expect >2000 characters for comprehensive prompt

- [ ] **20. Implement citation tracker**
      
      **What:** Create `backend/agent/citations.py`:
      - Class `CitationTracker` with methods:
        - `add_citation(source_type: str, source_id: str, metadata: dict)` — add to internal list
        - `get_citations() → list[str]` — return formatted citations
        - `format_citation(source_type, source_id, metadata) → str` — format based on type
      - Citation formats:
        - inspection: `f"[{source_id}]"` (e.g., [INS-0001-0203])
        - maintenance: `f"[{source_id}]"`
        - report: `f"[{source_id} Report]"`
        - manual: `f"[{metadata['well_type_code']} Manual §{metadata['section_number']}]"`
        - sop: `f"[SOP-{metadata['protocol_id'][:2]} §{metadata['protocol_id']}]"`
        - context_note: `f"[Note by {metadata['author']} on {metadata['date']}]"`
        - correction: `f"[Correction {source_id} by {metadata['author']} on {metadata['date']}]"`
      - Deduplicate citations in get_citations()
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\agent\citations.py`
      
      **Verify:** `python -c "from agent.citations import CitationTracker; tracker = CitationTracker(); tracker.add_citation('inspection', 'INS-0001-0203', {}); tracker.add_citation('manual', 'T200.md', {'well_type_code': 'T200', 'section_number': '9.3'}); print(tracker.get_citations())"` — expect ['[INS-0001-0203]', '[T200 Manual §9.3]']

- [ ] **21. Create LangGraph state machine**
      
      **What:** Create `backend/agent/agent.py`:
      - Define state schema: `AgentState = TypedDict('AgentState', {user_id: str, session_id: str, query: str, analysis: QueryAnalysis, tool_calls: list[ToolCall], tool_results: list[dict], conflicts: list[ConflictAlert], response: AgentResponse, citations: CitationTracker})`
      - Initialize Ollama client: `from langchain_community.llms import Ollama; llm = Ollama(base_url=os.getenv('OLLAMA_BASE_URL'), model=os.getenv('OLLAMA_MODEL'))`
      - Create 6 nodes:
        1. `analyze_query(state)` — LLM parses query into QueryAnalysis using system_prompt
        2. `plan_tools(state)` — LLM selects tools and parameters based on intent
        3. `execute_tools(state)` — Loop through tool_calls, execute each, collect results, add citations
        4. `check_conflicts(state)` — If memory_update was called, run conflict_detect
        5. `synthesize_response(state)` — LLM combines tool_results into natural language answer
        6. `finalize(state)` — Add visualization metadata, format citations, return AgentResponse
      - Define edges: START → analyze_query → plan_tools → execute_tools → conditional([if memory_update called] check_conflicts else synthesize_response) → finalize → END
      - Class `RigSyncAgent` with method `run(user_id: str, query: str) → AgentResponse`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\agent\agent.py` (partial — state machine skeleton)
      
      **Verify:** `python -c "from agent.agent import RigSyncAgent; agent = RigSyncAgent(); print(agent.graph.nodes.keys())"` — expect dict_keys(['analyze_query', 'plan_tools', 'execute_tools', 'check_conflicts', 'synthesize_response', 'finalize'])

- [ ] **22. Register tools in agent**
      
      **What:** Extend `agent.py`:
      - Import all 8 tools from FEAT-003
      - Create tools_registry: `{tool_name: (tool_instance, pydantic_schema)}`
      - In `execute_tools` node:
        - For each ToolCall in state.tool_calls:
          - Look up tool in registry
          - Validate parameters against schema
          - Call tool.execute(**parameters) or tool.method(**parameters)
          - Catch exceptions, store as error result
          - Extract citations from tool result metadata, add to state.citations
          - Store result: `{tool_name, parameters, result, execution_time_ms, error: str | null}`
      - If tool returns error, pass error message to LLM for replanning (add replan node in graph)
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\agent\agent.py` (complete execute_tools)
      
      **Verify:** `python -c "from agent.agent import RigSyncAgent; agent = RigSyncAgent(); print(len(agent.tools_registry))"` — expect 8

- [ ] **23. Implement visualization metadata generation**
      
      **What:** Extend `finalize` node in `agent.py`:
      - Based on `state.analysis.intent`, determine visualization_type:
        - status_check + single well → 'status_card'
        - multi_well_comparison or list query → 'table'
        - trend_analysis with temporal data → 'line_chart'
        - comparison across wells/areas/time → 'bar_chart'
        - query mentions location/area/geographic → 'map'
        - 2D comparison (e.g., area × month) → 'heatmap'
      - Generate visualization_data dict from tool_results:
        - For line_chart: `{x: [dates], series: [{name: 'Wellhead', y: [temps]}, {name: 'Ambient', y: [temps]}]}`
        - For table: `{columns: [col_names], rows: [[values]]}`
        - For map: `{points: [{lat, lon, label, color, popup_text}]}`
        - For bar_chart: `{x: [labels], y: [values], series_name: str}`
        - For status_card: `{well_id, status, metrics: [{label, value, unit}], alerts: [str]}`
      - Add to AgentResponse
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\agent\agent.py` (complete finalize node)
      
      **Verify:** `python -c "from agent.agent import RigSyncAgent; agent = RigSyncAgent(); response = agent.run('U-101', 'Show WELL-0001 temp trend last 13 weeks'); print(response.visualization_type)"` — expect 'line_chart'

- [ ] **24. Implement session and memory management**
      
      **What:** Create `backend/memory/memory_manager.py`:
      - Class `SessionManager`:
        - `create_session(user_id: str) → str` — generate session_id = f"sess_{user_id}_{int(time.time())}", create JSON file `data/memory/sessions/{session_id}.json` with `{session_id, user_id, created_at, messages: []}`
        - `get_session(session_id: str) → dict` — load from JSON
        - `add_message(session_id: str, role: str, content: str)` — append to messages array
        - `get_history(session_id: str, limit: int) → list[dict]` — return last N messages
      - Class `CorrectionTracker`:
        - `add_correction(correction: MemoryCorrection) → str` — append to appropriate JSON file (user/well/global), return correction_id
        - `get_corrections(entity_id: str, scope: str) → list[dict]` — load from JSON, filter by entity_id and scope
        - `check_conflicts(entity_id: str, field: str, new_value: any) → list[ConflictAlert]` — delegate to ConflictDetectTool
      - Both classes create directories/files as needed (pathlib.Path.mkdir(parents=True, exist_ok=True))
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\memory\memory_manager.py`
      
      **Verify:** `python -c "from memory.memory_manager import SessionManager; mgr = SessionManager(); sid = mgr.create_session('U-101'); mgr.add_message(sid, 'user', 'test'); hist = mgr.get_history(sid); print(len(hist))"` — expect 1

---

## Phase 5: FastAPI Backend & Testing (FEAT-005)

### Overview
Create REST API server with endpoints for chat, sessions, and data queries. Add comprehensive testing script. Depends on Phase 4 (agent must exist).

- [ ] **25. Create FastAPI app with CORS**
      
      **What:** Create `backend/main.py`:
      - `app = FastAPI(title='RigSync API', version='1.0.0', description='Agentic Asset Intelligence Copilot for Oil Field Operations')`
      - Add CORS middleware: `app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])`
      - Add startup event handler:
        ```python
        @app.on_event('startup')
        async def startup():
            # Verify data files exist
            assert Path('data/db/oilwells.db').exists(), "SQLite database not found"
            assert Path('data/chroma').exists(), "ChromaDB not found"
            assert Path('data/graph/knowledge_graph.json').exists(), "Knowledge graph not found"
            assert Path('data/rules/rules.json').exists(), "Rules not found"
            # Check Ollama
            try:
                ollama.list()
                logger.info("✓ Ollama: gemma4:e4b ready")
            except:
                logger.error("✗ Ollama not available. Start with: ollama serve")
            # Log data stats
            conn = sqlite3.connect('data/db/oilwells.db')
            well_count = conn.execute('SELECT COUNT(*) FROM wells').fetchone()[0]
            logger.info(f"✓ SQLite: {well_count} wells loaded")
            # ... similar for ChromaDB, graph, rules
        ```
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\main.py` (startup/shutdown only)
      
      **Verify:** `cd backend && uvicorn main:app --reload` — expect startup logs showing all subsystems ready

- [ ] **26. Implement POST /api/chat endpoint**
      
      **What:** Extend `main.py`:
      - Define request model: `class ChatRequest(BaseModel): user_id: str; session_id: str | None; query: str`
      - Define response model: `class ChatResponse(BaseModel): session_id: str; response: AgentResponse; conflicts: list[ConflictAlert] | None; processing_time_ms: int`
      - Endpoint:
        ```python
        @app.post('/api/chat', response_model=ChatResponse)
        async def chat(request: ChatRequest):
            start_time = time.time()
            # Create or load session
            if request.session_id is None:
                session_id = SessionManager().create_session(request.user_id)
            else:
                session_id = request.session_id
            # Add user message to history
            SessionManager().add_message(session_id, 'user', request.query)
            # Run agent
            try:
                agent = RigSyncAgent()
                response = agent.run(request.user_id, request.query)
            except OllamaConnectionError:
                raise HTTPException(status_code=503, detail='Ollama server not available. Start with: ollama serve')
            # Add assistant message to history
            SessionManager().add_message(session_id, 'assistant', response.answer)
            # Return response
            processing_time_ms = int((time.time() - start_time) * 1000)
            return ChatResponse(session_id=session_id, response=response, conflicts=response.conflicts, processing_time_ms=processing_time_ms)
        ```
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\main.py` (add /api/chat)
      
      **Verify:** `curl -X POST http://localhost:8000/api/chat -H 'Content-Type: application/json' -d '{"user_id": "U-101", "session_id": null, "query": "Is WELL-0001 producing?"}'` — expect response with answer, citations, visualization_type

- [ ] **27. Implement session and well data endpoints**
      
      **What:** Extend `main.py`:
      - `GET /api/sessions/{session_id}`:
        ```python
        @app.get('/api/sessions/{session_id}')
        async def get_session(session_id: str):
            session = SessionManager().get_session(session_id)
            if session is None:
                raise HTTPException(status_code=404, detail='Session not found')
            return session
        ```
      - `GET /api/wells` with query params `?area_id&well_type&status&limit`:
        ```python
        @app.get('/api/wells')
        async def list_wells(area_id: str | None = None, well_type: str | None = None, status: str | None = None, limit: int = 50):
            tool = SQLQueryTool()
            query = "SELECT w.asset_id, w.name, w.well_type, w.area_id, w.team_id, w.lat, w.lon, w.recorded_status, i.inspection_id, i.inspected_at, i.inspector_user_id FROM wells w LEFT JOIN (SELECT asset_id, MAX(inspected_at) as max_date FROM inspections GROUP BY asset_id) latest ON w.asset_id = latest.asset_id LEFT JOIN inspections i ON latest.asset_id = i.asset_id AND latest.max_date = i.inspected_at WHERE 1=1"
            params = {}
            if area_id:
                query += " AND w.area_id = :area_id"
                params['area_id'] = area_id
            # ... similar for well_type, status
            query += f" LIMIT :limit"
            params['limit'] = limit
            result = tool.execute(query, params)
            # Format as list of dicts
            return [dict(zip(result['columns'], row)) for row in result['rows']]
        ```
      - `GET /api/wells/{asset_id}`:
        - Query wells, equipment, last 5 inspections, last 5 maintenance, active context notes
        - Compute is_currently_producing using downtime_calc tool
        - Compute days_since_last_inspection
        - Run compliance_check for last 90 days
        - Return comprehensive well detail object
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\main.py` (add 3 endpoints)
      
      **Verify:** `curl http://localhost:8000/api/wells?area_id=SW-23&limit=5` — expect 5 wells; `curl http://localhost:8000/api/wells/WELL-0001` — expect detailed object with is_currently_producing computed

- [ ] **28. Implement health check endpoint**
      
      **What:** Extend `main.py`:
      - `GET /api/health`:
        ```python
        @app.get('/api/health')
        async def health_check():
            health = {
                'status': 'healthy',
                'ollama_available': False,
                'database_available': False,
                'chromadb_available': False,
                'graph_available': False,
                'rules_loaded': False,
                'uptime_seconds': int(time.time() - app.state.start_time)
            }
            # Check Ollama
            try:
                ollama.list()
                health['ollama_available'] = True
            except:
                pass
            # Check database
            try:
                conn = sqlite3.connect('data/db/oilwells.db')
                conn.execute('SELECT 1').fetchone()
                conn.close()
                health['database_available'] = True
            except:
                pass
            # ... similar for ChromaDB, graph, rules
            # Set overall status
            if all([health['ollama_available'], health['database_available'], health['chromadb_available'], health['graph_available'], health['rules_loaded']]):
                health['status'] = 'healthy'
            else:
                health['status'] = 'degraded'
            return health
        ```
      - Store app start time in `app.state.start_time = time.time()` in startup event
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\main.py` (complete)
      
      **Verify:** `curl http://localhost:8000/api/health` — expect {status: 'healthy', all booleans: true}

- [ ] **29. Create comprehensive test suite**
      
      **What:** Create `backend/scripts/test_queries.py`:
      - Define 18 test queries covering all scenarios:
        1. "Is WELL-0001 producing oil right now?" — expect status_card, citations include inspection ID
        2. "Which wells in Northeast Block 8 are not producing?" — expect table with 4 wells
        3. "Show WELL-0001 temperature chart for last 13 weeks" — expect line_chart
        4. "How many days was WELL-0042 down between April and July 2026?" — expect numeric answer with downtime_days
        5. "Which wells have late spill reports?" — expect list of violations with SR-01
        6. "The Oct 15 reading for WELL-0164 was wrong, should be 41.0°C" — expect conflict alert
        7. "What does the T200 manual say about production temperature?" — expect citation T200 Manual §9.3
        8. "Which wells had flowline leaks this year?" — expect list from maintenance table
        9. "List all wells in area SW-23" — expect 50 wells
        10. "Get equipment for WELL-0001" — expect 5 equipment items
        11. "Which wells missed inspections in October 2026?" — expect RC-01 violations
        12. "Show downtime trend for WELL-0001 in 2025" — expect bar_chart or line_chart
        13. "Which wells had RCA-triggering maintenance patterns?" — expect wells with 3+ corrective events on same equipment
        14. "Map all spills in 2026" — expect map visualization
        15. "Compare production status across all areas" — expect heatmap or bar_chart
        16. "What are the spill containment deadlines?" — expect SR-02: 4 hours from vector search
        17. "Who is responsible for WELL-0050?" — expect user from graph query
        18. "Show me wells with multiple corrections" — expect list from memory
      - For each query:
        - Send POST request to /api/chat
        - Validate response structure (answer not empty, citations list length ≥ 1, visualization_type is one of 6 types, processing_time < 30000ms)
        - Check expected content (e.g., for query 1, answer should mention "not producing" and "planned shut-in")
        - Log PASS/FAIL with reason
      - Generate summary report: "Test Results: X/18 PASSED, Y/18 FAILED"
      - Save detailed results to `results/test_results.json`
      
      **Files:** `c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\backend\scripts\test_queries.py`
      
      **Verify:** `python backend/scripts/test_queries.py` — expect "Test Results: 16/18 PASSED" (allow 2 failures due to LLM variability)

---

## Data Gotchas Found in Sample Data

### WELL-0001 Specific Observations
1. **Context note CTX-0001-003** (Oct 7, 2026): "Well shut in from 7 Oct for planned rod string replacement. Expected back online around 20 Oct." This explains why Oct 8 and Oct 15 inspections show not producing.
2. **Inspection INS-0001-0070** (Mar 7, 2024): Spill detected (3.1% area, 0.9 bbl). Context note CTX-0001-001 corrects this: "dark patch is rainwater mixed with soil, not crude. Not a spill." Demonstrates need for context note corrections.
3. **Maintenance MNT-0001-011** (Jan 12-16, 2024): Flowline corrosion leak caused **101 hours downtime** — longest single event for WELL-0001 in dataset.
4. **Maintenance report MNT-0001-002** (Mar 17-18, 2023): Spill was contained **5.3 hours** after discovery, violating SR-02 4-hour deadline. Compliance table shows "SR-02: **Not met**" — use this for compliance violation queries.
5. **Flowline equipment** repeats in multiple maintenance events (MNT-0001-002, MNT-0001-005, MNT-0001-008, MNT-0001-009, MNT-0001-011, MNT-0001-028, MNT-0001-029, MNT-0001-032): **8 corrective flowline events** — far exceeds 3-event RCA trigger from T200 manual §10.

### Production Status Edge Cases
- **Winter readings:** Jan 11, 2024 inspection shows wellhead_temp=8.4°C, ambient=4.0°C → diff=4.4°C, below T200 15°C threshold → not producing
- **Summer readings:** Jul 20, 2023 inspection shows wellhead_temp=62.2°C, ambient=38.4°C → diff=23.8°C, above T200 15°C threshold → producing (even though absolute temp is high, it's not from solar heating alone)

### Missing Data Patterns
- Some maintenance events have `report_file: null` (e.g., scheduled maintenance MNT-0001-001) — only corrective events with spills or violations have markdown reports
- Context notes have `inspection_id: null` when they're general operator feedback not tied to specific inspection
- Equipment table has some equipment without model specified (e.g., older installations)

---

## Summary

This plan delivers RigSync in 5 logical phases:

1. **Phase 1 (items 1-5):** Foundation — SQLite schema, data ingestion, business rules extraction
2. **Phase 2 (items 6-9):** Semantic layer — ChromaDB embeddings, NetworkX graph
3. **Phase 3 (items 10-17):** Business logic — 8 specialized agent tools
4. **Phase 4 (items 18-24):** Intelligence — LangGraph orchestration, memory/corrections
5. **Phase 5 (items 25-29):** API — FastAPI endpoints, testing suite

**Total:** 29 implementation items, each independently verifiable. Dependencies are clearly marked (Phase 3 needs 1+2, Phase 4 needs 3, Phase 5 needs 4).

**Key Design Decisions:**
- **Hybrid storage:** SQLite for time-series (optimized for temporal queries), ChromaDB for semantic search, NetworkX for relationships, JSON for append-only corrections
- **Production threshold extraction:** Parse from manual text with regex, store in well_types table, apply in downtime_calc tool
- **Correction provenance:** Every correction tracks who, when, why, scope with full traceability
- **Conflict detection:** Compare against 3 sources (SQLite, memory, context notes) with severity scoring
- **Tool-first architecture:** Agent orchestrates tools rather than embedding logic in agent code
- **Citation tracking:** Every data point used in response is cited with proper format

**Next Steps After Implementation:**
1. Test with frontend Next.js chat interface (not in this plan — frontend is separate feature)
2. Run evaluation queries from docs/evaluation-queries.md
3. Fine-tune agent prompts based on query performance
4. Add caching layer (Redis) for frequently accessed queries
5. Deploy with Docker Compose (Ollama + FastAPI + Next.js)
