# RigSync 🛢️⚡

**Autonomous Multi-Modal Asset Intelligence Copilot for Upstream Oil & Gas Operations**

[![FlytBase MLH](https://img.shields.io/badge/FlytBase-MLH%20Hackathon%202026-blue.svg)](https://organize.mlh.io/)
[![Model: Gemma 4](https://img.shields.io/badge/LLM-Gemma%204%20(Ollama)-green.svg)](https://ollama.com/library/gemma4)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20LangGraph-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend: React + Vite](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20Tailwind-61DAFB.svg)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **RigSync** bridges the gap between massive industrial field telemetry and operational decision-making. Built for the **FlytBase Asset Intelligence Challenge**, it orchestrates an autonomous 6-node agent over structured time-series data, vector embeddings, property graphs, and scoped memory to deliver audit-grade, cited answers in seconds.

---

## 📑 Table of Contents

- [The Challenge](#-the-challenge)
- [What Makes RigSync Different](#-what-makes-rigsync-different-why-we-win)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [How to Run the Project](#-how-to-run-the-project-step-by-step)
  - [Prerequisites](#1-prerequisites)
  - [Backend Setup (Python / FastAPI)](#2-backend-setup)
  - [Frontend Setup (React / Vite)](#3-frontend-setup)
  - [Running with Ollama & Gemma 4](#4-running-with-ollama--gemma-4)
  - [Troubleshooting Common Issues](#5-troubleshooting-common-run-issues)
- [Data Ingestion & Pipeline](#-data-ingestion--pipeline)
- [Evaluation Queries & Use Cases](#-evaluation-queries--use-cases)
- [REST API Reference](#-rest-api-reference)
- [Project Directory Structure](#-project-directory-structure)
- [Future Roadmap](#-future-roadmap)
- [Contributors & License](#-contributors--license)

---

## 🎯 The Challenge

An upstream oil operator oversees **600+ wells** distributed across **7 geographic blocks** managed by **4 production teams**. Every week, autonomous drones inspect wellheads, maintenance crews replace components, field operators write shift logs, and regulatory agencies update compliance mandates.

This generates heterogeneous, siloed, and often conflicting data streams:
- 📊 **114,000+ weekly drone inspection logs**: Thermal differentials ($\Delta T$), flowline pressures, spill detections.
- 🔧 **5,700+ maintenance work orders**: Component replacements, labor hours, revised costs ($USD).
- 📄 **Thousands of free-text reports**: Root-cause analyses (RCA), failure logs, safety hazards.
- 📋 **SOPs, MOCs & Regulatory Letters**: Standard operating procedures, management-of-change temporary bypass approvals, pump recall notices, and State Commission directives.
- 💬 **Human shift notes & late corrections**: Field observations ("pump jack not moving"), verbal handoffs ("Nathan told me..."), and recalibration overrides.

**The Operator's Dilemma:**
> *"A well's database status says `active`, but the latest drone thermal delta is only 3°C above ambient, while an operator note from yesterday mentions a planned rod-string repair. Is the well actually producing oil right now? Are we violating our 24-hour spill reporting rule?"*

Standard dashboards cannot correlate these disjointed signals, and simple vector-search RAG models hallucinate or miss temporal sequencing. **RigSync solves this through deterministic multi-agent reasoning and domain-aware physical models.**

---

## 🚀 What Makes RigSync Different? (Why We Win)

Unlike conventional RAG chatbots that merely retrieve chunks and summarize them, RigSync was engineered from first principles for heavy industrial assets:

| Dimension | Standard RAG / Naive Chatbots | RigSync Asset Copilot |
|---|---|---|
| **Reasoning Engine** | Single-turn vector chunk retrieval (top-$k$ similarity) | **Deterministic 6-Node LangGraph State Machine** dynamically planning queries across SQL, vector, graph, and memory |
| **Physical Status Logic** | Blindly trusts database column `recorded_status: "active"` | **Domain-Specific Thermal Differential Engine (OPS-3)**: Derives real status from ambient delta ($\Delta T \ge 15^\circ\text{C}$ for T200, $\ge 18^\circ\text{C}$ for T350, $\ge 22^\circ\text{C}$ for T500) |
| **Downtime Calculation** | Sums work order labor duration ($4\text{ hours}$) | **Production Cycle Downtime**: Calculates downtime based on 7-day weekly thermal inspection failure intervals ($7\text{ days per non-producing cycle}$) |
| **Human vs. Sensor Conflicts** | Ignores contradictions or merges conflicting text | **Autonomous Conflict Detection Engine**: Actively flags when physical telemetry contradicts human operator notes (e.g. thermal delta indicates pumping, but note states pump jack stalled) |
| **Memory & Provenance** | Unstructured chat history buffer | **3-Tier Scoped Memory**: Separates private operator preferences from global asset truth, while tracking hearsay attribution (`"Nathan told me..."`) and verification status |
| **Regulatory Compliance** | Keyword search over PDF files | **Deterministic Rule Engine**: Encodes SOPs (OPS-1 to OPS-6), Spill Response (SR-01 to SR-04), and Commission Directives (RC-01 to RC-05) into verifiable logic |
| **Auditability** | Vague references or hallucinations | **Strict Citation Tracking**: Every claim is linked to immutable source IDs (`[INS-0151-0201]`, `[MNT-0042]`, `[SOP-OPS:OPS-1]`, `[MOC-2026-031]`) |
| **Privacy & Infrastructure** | Cloud API lock-in with sensitive field telemetry | **Local Air-Gapped Deployment**: Powered by **Gemma 4** running on-premise via Ollama with 64K context window |

---

## 🏗️ System Architecture

RigSync decouples presentation, deterministic agentic planning, and multi-modal storage across four synchronized layers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND CLIENT (React 18 + Vite + Tailwind)                    │
│   • Enterprise Field Ops Dashboard         • Real-time Inline Citation Badges          │
│   • Multi-User Persona Switcher            • Dynamic Generative UI (Cards, Tables,     │
│     (Supervisors, Operators, HSE Officers)   Line Charts, Bar Charts, Map Views)       │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP REST / WebSocket (/api/chat, /api/users)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND API GATEWAY (FastAPI + Python 3.10+)                    │
│   • Endpoint Routing & Session Management  • CORS Middleware & Request Validation      │
│   • Pydantic Schemas & State Serialization • User Isolation & Security Filters         │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
               LangGraph Autonomous Agent State Machine (backend/agent/agent.py)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                        │
│   [ 1. analyze_query ] ──► [ 2. plan_tools ] ──► [ 3. execute_tools ]                  │
│            ▲                                              │                            │
│            │ (Re-query if conflict)                       ▼                            │
│            └──────────────────────────────────── [ 4. check_conflicts ]                │
│                                                           │ (No conflict)              │
│                                                           ▼                            │
│   [ 6. finalize ] ◄───────────────────────────── [ 5. synthesize_response ]            │
│          │                                                                             │
└──────────┼─────────────────────────────────────────────────────────────────────────────┘
           │
           │ Orchestrates across 8 Specialized Agent Tools
           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  8 SPECIALIZED AGENT TOOLS                             │
│  1. sql_query        : Safe parameterized queries over 14 relational tables            │
│  2. vector_search    : Semantic similarity search across ChromaDB collections          │
│  3. graph_query      : NetworkX property graph traversal for well/flowline topology     │
│  4. downtime_calc    : Domain calculation based on weekly inspection intervals         │
│  5. compliance_check : Automated validation against SOP, MOC, and recall rules         │
│  6. memory_retrieval : Scoped retrieval of user preferences and verified asset memory  │
│  7. memory_update    : Records corrections with full author/timestamp provenance       │
│  8. conflict_detect  : Detects contradictions between sensor readings and shift notes  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                4-TIER HYBRID STORAGE TOPOLOGY                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │   SQLite DB      │  │  ChromaDB Store  │  │ NetworkX Graph   │  │  JSON Memory   │  │
│  │ 14 Tables        │  │ 4 Collections    │  │ Topology & Flow  │  │ Audit Logs &   │  │
│  │ 114K+ Inspections│  │ SOPs, MOCs, RCAs │  │ Wells, Pads,     │  │ Scoped User    │  │
│  │ Repairs & Costs  │  │ Embeddings       │  │ Pipelines, Teams │  │ Preferences    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └────────────────┘  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                            LOCAL LLM INFERENCE (Ollama Engine)                         │
│   • Gemma 4 (e4b / 12b / 26b)             • 64,000 Token Context Window                │
│   • Zero Cloud API Costs                  • Air-Gapped Industrial Security             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 1. 🤖 LangGraph 6-Node Agentic State Machine
Instead of a single unguided prompt, query execution flows through 6 discrete, auditable nodes:
1. **`analyze_query`**: Extracts entities (Well IDs, Areas, Dates, Personas) and classifies operational intent.
2. **`plan_tools`**: Formulates a tool execution strategy (e.g. query SQL for telemetry, then vector search for MOC approval).
3. **`execute_tools`**: Runs tools safely with parameter bounds and error trapping.
4. **`check_conflicts`**: Cross-validates telemetry against operator shift notes and known overrides.
5. **`synthesize_response`**: Merges numerical facts, SOP clauses, and quotes into natural language with citations.
6. **`finalize`**: Packages markdown text with structured visual metadata (tables, cards, charts).

### 2. 🧠 3-Tier Enterprise Memory System
- **User-Scoped Preferences**: If Nathan Pierce requests: *"Sort wells by area and display costs in thousands"*, this preference is saved exclusively to Nathan's profile and never impacts other supervisors.
- **Global Asset Truth**: When a technician confirms a pump replacement on `WELL-0333`, all users immediately see the updated asset state across future sessions.
- **Hearsay & Provenance Auditing**: Verbal handoffs (e.g. *"Olivia: Nathan told me WELL-0577 was swapped"*) are logged with exact attribution (`author: Olivia`, `source: Nathan`) and tagged as *Unconfirmed* until validated by work order telemetry.

### 3. 🔍 Physical Domain Logic & Rule Automation
- **Thermal Production Status**: Evaluates wellhead temperature against ambient reading according to equipment specs (T200, T350, T500).
- **Spill Reporting Engine**: Automatically checks spill records against rules **SR-01** (spills $\ge 5\text{ bbl}$ require report within 24 hours) and **RC-01 to RC-05** from regulatory directives.
- **Temporary Flowline MOC Tracker**: Cross-references bypass installations against Management-of-Change expiration dates.

### 4. 📊 Generative UI & Multi-User Field Persona Switcher
- **Live User Switching**: Switch seamlessly between Field Operators, Production Supervisors, and HSE Officers to test access controls, memory isolation, and persona-specific answers.
- **Generative Visualizations**: Generates dynamic UI elements on the fly—well status indicator cards, sorting data tables, temperature time-series graphs, and geospatial spill incident maps.

---

## 💻 How to Run the Project (Step-by-Step)

Follow these clear, bulletproof steps to run RigSync locally.

### 1. Prerequisites

- **Python 3.10 or 3.11** installed.
- **Node.js 18+** and **npm** installed.
- **Ollama** installed ([Download Ollama](https://ollama.com/download)).
- **Git** installed.

---

### 2. Backend Setup

Open a terminal and navigate to the `RigSync/backend` folder:

```bash
cd RigSync/backend
```

#### Step A: Create and Activate Virtual Environment

> [!IMPORTANT]
> **Windows Users**: On Windows systems, invoking `py -3.12` or `python` can accidentally invoke your global Python installation instead of your virtual environment. Always activate the venv first or use the direct venv Python binary path!

**On Windows (PowerShell):**
```powershell
# Create venv if not already created
python -m venv venv

# Activate venv
.\venv\Scripts\Activate.ps1

# Verify venv is active (should point to backend\venv\Scripts\python.exe)
Get-Command python | Select-Object -ExpandProperty Source
```

**On Windows (Git Bash / Bash):**
```bash
# Create venv if not already created
python -m venv venv

# Activate venv
source venv/Scripts/activate

# Verify
which python
```

**On macOS / Linux:**
```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Verify
which python3
```

#### Step B: Install Python Dependencies

With the virtual environment activated:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

*(Key packages installed: `fastapi`, `uvicorn`, `langgraph`, `langchain`, `chromadb`, `sentence-transformers`, `networkx`, `pandas`, `pydantic`)*

#### Step C: Start the Backend Server

Run the backend via `python main.py` or `uvicorn`:

```bash
# Option 1: Standard runner
python main.py

# Option 2: Direct Uvicorn command
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **Direct Windows Execution (Without Activating):**
> If you prefer running without activating your shell:
> ```powershell
> .\venv\Scripts\python.exe main.py
> ```

The API is now live at **`http://localhost:8000`**.  
Interactive Swagger docs: **`http://localhost:8000/docs`**.

---

### 3. Frontend Setup

Open a **new terminal** window and navigate to `RigSync/frontend`:

```bash
cd RigSync/frontend
```

#### Step A: Install Frontend Dependencies

```bash
npm install
```

#### Step B: Launch Vite Dev Server

```bash
npm run dev
```

The frontend will start instantly at **`http://localhost:3000`** (or `http://localhost:5173`).  
Open your browser and navigate to **`http://localhost:3000`**.

> **Note on API Proxy:** Vite is configured via `vite.config.ts` to automatically proxy all `/api` requests to `http://localhost:8000`.

---

### 4. Running with Ollama & Gemma 4

RigSync is powered by Google's open-weights **Gemma 4** running locally via Ollama for zero API costs and full data privacy.

1. **Pull the model** (in any terminal):
   ```bash
   # For 16GB RAM systems (Recommended)
   ollama pull gemma4:e4b

   # For 32GB+ RAM systems
   ollama pull gemma4:12b
   ```

2. **Configure 64K Context Window**:
   Set context length so the model can digest long SOP manuals and fleet documents:
   - **PowerShell (Windows)**:
     ```powershell
     $env:OLLAMA_CONTEXT_LENGTH=64000
     ```
   - **Linux / macOS**:
     ```bash
     export OLLAMA_CONTEXT_LENGTH=64000
     ```
   - *(Or configure context length in the Ollama desktop application settings).*

3. **Ensure Ollama Service is Running**:
   ```bash
   ollama serve
   ```

---

### 5. Troubleshooting Common Run Issues

#### Issue 1: `ModuleNotFoundError: No module named 'fastapi'` on Windows
- **Cause**: Windows has a `py` launcher (`py -3.12`) which executes global Python regardless of shell activation.
- **Solution**: Do NOT use `py -3.12 main.py`. Instead, make sure your venv is active and run `python main.py`, or call the virtual environment executable directly:
  ```powershell
  .\venv\Scripts\python.exe main.py
  ```

#### Issue 2: PowerShell Execution Policy error on `Activate.ps1`
- **Cause**: PowerShell restricts script execution by default.
- **Solution**: Run this command once in PowerShell:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

#### Issue 3: Port 8000 or Port 3000 Already in Use
- **Backend Port Change**: Run `uvicorn main:app --port 8001 --reload` and update `target` in `frontend/vite.config.ts`.
- **Frontend Port Change**: Vite will automatically offer the next available port (e.g. 3001).

---

## 🔄 Data Ingestion & Pipeline

RigSync includes ingestion scripts inside `backend/scripts/` to rebuild or populate the multi-modal storage layer from raw dataset files:

```bash
cd RigSync/backend

# Ensure venv is active, then run:

# 1. Initialize SQLite schema (14 tables)
python scripts/init_database.py

# 2. Ingest 600 wells, time-series inspections, and maintenance records
python scripts/ingest_wells.py

# 3. Ingest fleet data (users, teams, areas, and roles)
python scripts/ingest_fleet.py

# 4. Ingest free-text maintenance reports
python scripts/ingest_reports.py

# 5. Build vector embeddings in ChromaDB for SOPs, MOCs, and manuals
python scripts/build_embeddings.py

# 6. Construct NetworkX knowledge graph for flowlines and equipment
python scripts/build_knowledge_graph.py

# 7. Parse SOP and MOC business rules into structured JSON
python scripts/parse_sops.py
```

---

## 🧪 Evaluation Queries & Use Cases

RigSync was evaluated against complex operational questions on the full **600-well fleet** (as of 15 January 2027):

### 1. Production Status & Thermal Reasoning
- **Query**: *"Is WELL-0001 producing oil right now?"*
- **RigSync Behavior**: Pulls latest drone thermal inspection (`INS-0001-0203`), checks ambient differential ($\Delta T = 3.2^\circ\text{C}$ vs $15^\circ\text{C}$ threshold required by T200 manual), cross-references operator note from Oct 7 citing a planned shut-in, and answers: **Not producing oil (planned shutdown)** with full citations.

### 2. Multi-Well Anomaly & Gas Leakage SOP
- **Query**: *"Since 1 Nov 2026, every time an operator note reports gas at a well, did we get someone out to that well in time under our operating procedures?"*
- **RigSync Behavior**: Scans `context.jsonl` for gas leak reports, joins with subsequent work orders (`maintenance.jsonl`), calculates elapsed response hours against SOP deadlines, and renders a structured table displaying `Well`, `Reported At`, `Response Record`, `Hours`, `Deadline`, and `Met / Missed`.

### 3. Temporary Flowline Bypass Auditing (MOC)
- **Query**: *"Across all areas, which temporary flowline bypasses are in place right now, and is each one allowed?"*
- **RigSync Behavior**: Searches maintenance logs for bypass installations, matches each against Management-of-Change memos (`MOC-2026-031`, etc.), checks expiration dates relative to 15 Jan 2027, and flags expired or unapproved bypasses.

### 4. Recalled Supplier Pumps & Cross-Session Memory
- **Turn 1 (Nathan Pierce)**: *"WELL-0333's recalled pump was swapped out yesterday. The work order isn't in the system yet. Please count it as replaced from now on."*
- **Turn 2 (Robert Hayes)**: *"Which recalled pumps are still in the ground right now?"*
- **RigSync Behavior**: Nathan's verbal update is recorded in global memory with provenance. When Robert asks in a separate session, `WELL-0333` is excluded from the recall list, noting: *"Excluded based on field swap report by Nathan Pierce on 14 Jan 2027."*

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Main query endpoint. Accepts query, `session_id`, and `user_id`. Returns agent response, citations, and visual metadata. |
| `GET` | `/api/users` | Lists all 27 field operators, supervisors, and HSE personnel for testing. |
| `GET` | `/api/teams` | Returns all 4 production teams and their assigned geographic blocks. |
| `GET` | `/api/wells` | Fetches well records with filtering by area, status, and well type. |
| `GET` | `/api/sessions` | Retrieves session history and message count for a given user. |
| `POST` | `/api/sessions` | Creates a new isolated chat session. |
| `POST` | `/api/corrections`| Manually records a factual asset correction with user attribution. |
| `GET` | `/api/health` | Returns backend operational health and database connection status. |
| `GET` | `/api/stats` | Aggregated system metrics (total wells, inspections, vector count). |

---

## 📁 Project Directory Structure

```
RigSync/
├── backend/                         # FastAPI & LangGraph Backend
│   ├── agent/                       # Agent Core
│   │   ├── agent.py                 # 6-Node LangGraph State Machine
│   │   ├── citations.py             # Citation Tracking System
│   │   ├── prompts.py               # System & Tool Prompts
│   │   └── schemas.py               # Pydantic Schemas
│   ├── data/                        # Multi-Tier Data Storage
│   │   ├── chroma/                  # ChromaDB Vector Store
│   │   ├── db/                      # SQLite DB (oilwells.db, schema.sql)
│   │   ├── graph/                   # NetworkX Knowledge Graph
│   │   ├── memory/                  # Scoped JSON Memory & Sessions
│   │   └── rules/                   # Extracted SOP & MOC Rules
│   ├── memory/                      # Memory Subsystem
│   │   ├── memory_manager.py        # Session & Preference Manager
│   │   └── correction_tracker.py    # Fact Provenance Tracker
│   ├── scripts/                     # Data Ingestion & Build Scripts
│   │   ├── build_embeddings.py      # ChromaDB Embedding Builder
│   │   ├── build_knowledge_graph.py # NetworkX Graph Builder
│   │   ├── ingest_fleet.py          # Users, Teams, Areas Ingestion
│   │   ├── ingest_reports.py        # Maintenance Reports Ingestion
│   │   ├── ingest_wells.py          # Wells & Inspections Ingestion
│   │   ├── init_database.py         # SQLite Schema Setup
│   │   ├── parse_sops.py            # SOP & MOC Rule Parser
│   │   └── test_queries.py          # Automated Test Harness
│   ├── tools/                       # 8 Specialized Agent Tools
│   │   ├── compliance_check.py      # SOP Rule Checker
│   │   ├── conflict_detect.py       # Sensor vs Human Discrepancy Finder
│   │   ├── downtime_calc.py         # Production Downtime Calculator
│   │   ├── graph_query.py           # NetworkX Property Graph Query
│   │   ├── memory_retrieval.py      # Scoped User Memory Fetcher
│   │   ├── memory_update.py         # Asset Fact & Memory Updater
│   │   ├── sql_query.py             # Safe Parameterized SQL Query
│   │   └── vector_search.py         # Semantic Search Tool
│   ├── main.py                      # FastAPI Application Entrypoint
│   └── requirements.txt             # Python Dependencies
│
├── frontend/                        # React 18 + Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/                # Chat Interface & Message Bubbles
│   │   │   │   ├── Chat.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   └── MessageList.tsx
│   │   │   └── Layout/              # Navigation & Header
│   │   │       ├── Header.tsx       # User Persona Switcher & Session Controls
│   │   │       └── Sidebar.tsx      # Fleets, Areas, and Status Filters
│   │   ├── contexts/
│   │   │   └── SessionContext.tsx   # React Session & Persona State
│   │   ├── types/
│   │   │   └── index.ts             # TypeScript Interfaces
│   │   ├── App.tsx                  # Root Application Component
│   │   ├── main.tsx                 # Vite Entrypoint
│   │   └── index.css                # Tailwind Styling
│   ├── index.html                   # HTML Entrypoint
│   ├── package.json                 # Node Dependencies & Scripts
│   ├── tailwind.config.js           # Tailwind Configuration
│   ├── tsconfig.json                # TypeScript Configuration
│   └── vite.config.ts               # Vite Configuration & Backend Proxy
│
├── scripts/                         # Benchmark & Deep Analysis Scripts
│   ├── analyze_q3.py                # Gas Leak Response Analysis
│   ├── analyze_q4.py                # Flowline Bypass MOC Analysis
│   ├── analyze_q5.py                # Regulator Spill Compliance
│   ├── analyze_q6.py                # Discrepancy & Ground Truth Check
│   ├── analyze_recalled_pumps.py    # Recalled Equipment Lineage
│   └── generate_html_report.py      # Visual Report Generator
│
├── SUBMISSION_REPORT.md             # Complete Technical Submission Document
├── .env.example                     # Environment Variables Template
├── LICENSE                          # MIT License
└── README.md                        # Documentation (You are here)
```

---

## 🔮 Future Roadmap

- [ ] **Predictive Failure Forecasting**: Integrate XGBoost time-series anomaly detection on thermal variance to flag impending pump lockups 14 days before failure.
- [ ] **Native SCADA & MQTT Telemetry**: Ingest real-time IoT sensor streams directly from wellhead RTUs.
- [ ] **Offline Edge Sync**: Packaged PWA for field technicians on remote rigs with intermittent satellite connectivity.
- [ ] **Automated Work-Order Dispatch**: Direct integration with SAP PM / Maximo to auto-draft repair tickets upon compliance breach detection.

---

## 🏆 Hackathon Submission Details

- **Event**: FlytBase Asset Intelligence Copilot Challenge — Major League Hacking (MLH)
- **Award Tracks**:
  - 🥇 **Asset Intelligence Copilot Challenge** (Primary)
  - 🥈 **Best Use of Gemma 4** (Local on-premise inference with 64K context)
- **Author**: Divyansh Nagar ([@inddivyansh](https://github.com/inddivyansh))
- **License**: [MIT](LICENSE)

<div align="center">
  <sub>Built with precision for mission-critical energy operations.</sub>
</div>
