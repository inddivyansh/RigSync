"""
FastAPI backend for RigSync - Asset Intelligence Copilot.
Provides REST API for chat, sessions, and well data access.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from agent.agent import RigSyncAgent
from memory.memory_manager import SessionManager, CorrectionTracker


# Pydantic models for API
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str = Field(..., description="User query")
    session_id: Optional[str] = Field(None, description="Session ID (optional, will create if not provided)")
    user_id: str = Field(..., description="User ID")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    session_id: str
    metadata: Dict[str, Any]


class SessionCreate(BaseModel):
    """Request model for creating a session."""
    user_id: str


class SessionResponse(BaseModel):
    """Response model for session info."""
    session_id: str
    user_id: str
    created_at: str
    message_count: int
    correction_count: int


class CorrectionRequest(BaseModel):
    """Request model for adding a correction."""
    well_id: Optional[str] = None
    field_name: str
    incorrect_value: str
    correct_value: str
    correction_reason: str
    corrected_by: str


class CorrectionResponse(BaseModel):
    """Response model for correction."""
    correction_id: str
    message: str


# Initialize FastAPI app
app = FastAPI(
    title="RigSync API",
    description="Asset Intelligence Copilot for Oil & Gas Well Management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent = None
session_manager = None
correction_tracker = None


@app.on_event("startup")
async def startup_event():
    """Initialize agent and managers on startup."""
    global agent, session_manager, correction_tracker
    
    agent = RigSyncAgent(
        db_path="backend/data/db/oilwells.db",
        chroma_path="backend/data/chroma",
        graph_path="backend/data/graph/knowledge_graph.json",
        memory_dir="backend/data/memory"
    )
    
    session_manager = SessionManager("backend/data/memory")
    correction_tracker = CorrectionTracker("backend/data/db/oilwells.db")
    
    print("✅ RigSync agent initialized")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RigSync API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/api/chat",
            "/api/sessions",
            "/api/corrections",
            "/api/wells",
            "/api/health"
        ]
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_initialized": agent is not None
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - main interface for querying the RigSync agent.
    
    Accepts a natural language query and returns an intelligent response
    with citations and metadata.
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Get or create session
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        session_manager.create_session(session_id, request.user_id)
    else:
        # Ensure session exists
        session = session_manager.get_session(session_id)
        if not session:
            session_manager.create_session(session_id, request.user_id)
    
    try:
        # Execute query
        result = await agent.query(
            query=request.query,
            session_id=session_id,
            user_id=request.user_id
        )
        
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            metadata=result["metadata"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreate):
    """Create a new chat session."""
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    session_id = str(uuid.uuid4())
    session = session_manager.create_session(session_id, request.user_id)
    
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        message_count=len(session.messages),
        correction_count=len(session.corrections)
    )


@app.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions(user_id: Optional[str] = None):
    """List all sessions, optionally filtered by user."""
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    sessions = session_manager.list_sessions(user_id)
    
    return [
        SessionResponse(
            session_id=s["session_id"],
            user_id=s["user_id"],
            created_at=s["created_at"],
            message_count=s["message_count"],
            correction_count=s["correction_count"]
        )
        for s in sessions
    ]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session with full history."""
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session.to_dict()


@app.post("/api/corrections", response_model=CorrectionResponse)
async def add_correction(request: CorrectionRequest):
    """Add a user correction."""
    if correction_tracker is None:
        raise HTTPException(status_code=503, detail="Correction tracker not initialized")
    
    try:
        correction_id = correction_tracker.add_correction(
            well_id=request.well_id,
            field_name=request.field_name,
            incorrect_value=request.incorrect_value,
            correct_value=request.correct_value,
            correction_reason=request.correction_reason,
            corrected_by=request.corrected_by,
            correction_source="api"
        )
        
        return CorrectionResponse(
            correction_id=correction_id,
            message=f"Correction recorded: {correction_id}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add correction: {str(e)}")


@app.get("/api/corrections")
async def get_corrections(
    user_id: Optional[str] = None,
    well_id: Optional[str] = None,
    field_name: Optional[str] = None
):
    """Get corrections, optionally filtered."""
    if correction_tracker is None:
        raise HTTPException(status_code=503, detail="Correction tracker not initialized")
    
    if user_id:
        corrections = correction_tracker.get_user_corrections(user_id)
    elif well_id:
        corrections = correction_tracker.get_well_corrections(well_id)
    elif field_name:
        corrections = correction_tracker.get_global_corrections(field_name)
    else:
        corrections = correction_tracker.get_global_corrections()
    
    return {"corrections": corrections, "count": len(corrections)}


@app.get("/api/corrections/stats")
async def get_correction_stats():
    """Get correction statistics."""
    if correction_tracker is None:
        raise HTTPException(status_code=503, detail="Correction tracker not initialized")
    
    return correction_tracker.get_correction_stats()


@app.get("/api/wells")
async def list_wells(
    area: Optional[str] = None,
    status: Optional[str] = None,
    well_type: Optional[str] = None,
    limit: int = 50
):
    """List wells with optional filters."""
    import sqlite3
    
    conn = sqlite3.connect("backend/data/db/oilwells.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sql = "SELECT well_id, well_type, status, area, latitude, longitude FROM wells WHERE 1=1"
    params = []
    
    if area:
        sql += " AND area = ?"
        params.append(area)
    
    if status:
        sql += " AND status = ?"
        params.append(status)
    
    if well_type:
        sql += " AND well_type = ?"
        params.append(well_type)
    
    sql += f" LIMIT ?"
    params.append(limit)
    
    cursor.execute(sql, params)
    wells = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"wells": wells, "count": len(wells)}


@app.get("/api/wells/{well_id}")
async def get_well(well_id: str):
    """Get detailed information about a specific well."""
    import sqlite3
    
    conn = sqlite3.connect("backend/data/db/oilwells.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get well details
    cursor.execute("""
        SELECT * FROM wells WHERE well_id = ?
    """, (well_id,))
    
    well = cursor.fetchone()
    if not well:
        conn.close()
        raise HTTPException(status_code=404, detail="Well not found")
    
    well_data = dict(well)
    
    # Get recent inspections
    cursor.execute("""
        SELECT * FROM inspections 
        WHERE well_id = ? 
        ORDER BY inspection_date DESC 
        LIMIT 5
    """, (well_id,))
    well_data["recent_inspections"] = [dict(row) for row in cursor.fetchall()]
    
    # Get recent maintenance
    cursor.execute("""
        SELECT * FROM maintenance 
        WHERE well_id = ? 
        ORDER BY maintenance_date DESC 
        LIMIT 5
    """, (well_id,))
    well_data["recent_maintenance"] = [dict(row) for row in cursor.fetchall()]
    
    # Get compliance status
    cursor.execute("""
        SELECT rule_id, severity, message, detected_date 
        FROM compliance_violations 
        WHERE well_id = ? 
        ORDER BY detected_date DESC 
        LIMIT 5
    """, (well_id,))
    well_data["compliance_violations"] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return well_data


@app.get("/api/wells/{well_id}/downtime")
async def get_well_downtime(well_id: str):
    """Calculate downtime for a specific well."""
    from tools.downtime_calc import calculate_downtime
    
    try:
        result = calculate_downtime(well_id, "backend/data/db/oilwells.db")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Downtime calculation failed: {str(e)}")


@app.get("/api/wells/{well_id}/compliance")
async def get_well_compliance(well_id: str):
    """Check compliance for a specific well."""
    from tools.compliance_check import check_compliance
    
    try:
        result = check_compliance(well_id, "backend/data/db/oilwells.db")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")


@app.get("/api/areas")
async def list_areas():
    """List all operational areas."""
    import sqlite3
    
    conn = sqlite3.connect("backend/data/db/oilwells.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM areas")
    areas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"areas": areas, "count": len(areas)}


@app.get("/api/teams")
async def list_teams():
    """List all operational teams."""
    import sqlite3
    
    conn = sqlite3.connect("backend/data/db/oilwells.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM teams")
    teams = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"teams": teams, "count": len(teams)}


@app.get("/api/users")
async def list_users():
    """List all users."""
    import sqlite3
    
    conn = sqlite3.connect("backend/data/db/oilwells.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id, name, role, team FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"users": users, "count": len(users)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
