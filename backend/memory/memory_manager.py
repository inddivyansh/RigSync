"""
Memory management for RigSync agent.
Handles session state, conversation history, and correction tracking.
"""

import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SessionMessage:
    """A single message in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    """State for a single conversation session."""
    session_id: str
    user_id: str
    created_at: str
    messages: List[SessionMessage] = field(default_factory=list)
    corrections: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata
                }
                for msg in self.messages
            ],
            "corrections": self.corrections,
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create session from dictionary."""
        messages = [
            SessionMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp", ""),
                metadata=msg.get("metadata", {})
            )
            for msg in data.get("messages", [])
        ]
        
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            created_at=data["created_at"],
            messages=messages,
            corrections=data.get("corrections", []),
            context=data.get("context", {})
        )


class SessionManager:
    """Manages conversation sessions and persistence."""
    
    def __init__(self, storage_dir: str = "backend/data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, SessionState] = {}
    
    def create_session(self, session_id: str, user_id: str) -> SessionState:
        """Create a new session."""
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now().isoformat()
        )
        self.sessions[session_id] = session
        self._save_session(session)
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get an existing session."""
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Try to load from disk
        session = self._load_session(session_id)
        if session:
            self.sessions[session_id] = session
        return session
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        message = SessionMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        session.messages.append(message)
        self._save_session(session)
    
    def add_correction(self, session_id: str, correction: Dict[str, Any]):
        """Add a correction to a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.corrections.append(correction)
        self._save_session(session)
    
    def update_context(self, session_id: str, context_updates: Dict[str, Any]):
        """Update session context."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.context.update(context_updates)
        self._save_session(session)
    
    def get_conversation_history(
        self,
        session_id: str,
        max_messages: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Get conversation history formatted for LLM."""
        session = self.get_session(session_id)
        if not session:
            return []
        
        messages = session.messages
        if max_messages:
            messages = messages[-max_messages:]
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    
    def _save_session(self, session: SessionState):
        """Save session to disk."""
        file_path = self.storage_dir / f"{session.session_id}.json"
        with open(file_path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)
    
    def _load_session(self, session_id: str) -> Optional[SessionState]:
        """Load session from disk."""
        file_path = self.storage_dir / f"{session_id}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return SessionState.from_dict(data)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None
    
    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by user."""
        sessions = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                if user_id is None or data.get("user_id") == user_id:
                    sessions.append({
                        "session_id": data["session_id"],
                        "user_id": data["user_id"],
                        "created_at": data["created_at"],
                        "message_count": len(data.get("messages", [])),
                        "correction_count": len(data.get("corrections", []))
                    })
            except Exception:
                continue
        
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)


class CorrectionTracker:
    """Tracks corrections and learns from user feedback."""
    
    def __init__(self, db_path: str = "backend/data/db/oilwells.db"):
        self.db_path = db_path
    
    def get_user_corrections(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent corrections by a user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                correction_id,
                well_id,
                field_name,
                incorrect_value,
                correct_value,
                correction_reason,
                corrected_by,
                correction_date,
                correction_source
            FROM user_corrections
            WHERE corrected_by = ?
            ORDER BY correction_date DESC
            LIMIT ?
        """, (user_id, limit))
        
        corrections = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return corrections
    
    def get_well_corrections(self, well_id: str) -> List[Dict[str, Any]]:
        """Get all corrections for a well."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                correction_id,
                well_id,
                field_name,
                incorrect_value,
                correct_value,
                correction_reason,
                corrected_by,
                correction_date,
                correction_source
            FROM user_corrections
            WHERE well_id = ?
            ORDER BY correction_date DESC
        """, (well_id,))
        
        corrections = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return corrections
    
    def get_global_corrections(self, field_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get global corrections, optionally filtered by field."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if field_name:
            cursor.execute("""
                SELECT 
                    correction_id,
                    well_id,
                    field_name,
                    incorrect_value,
                    correct_value,
                    correction_reason,
                    corrected_by,
                    correction_date,
                    correction_source
                FROM user_corrections
                WHERE field_name = ? AND well_id IS NULL
                ORDER BY correction_date DESC
            """, (field_name,))
        else:
            cursor.execute("""
                SELECT 
                    correction_id,
                    well_id,
                    field_name,
                    incorrect_value,
                    correct_value,
                    correction_reason,
                    corrected_by,
                    correction_date,
                    correction_source
                FROM user_corrections
                WHERE well_id IS NULL
                ORDER BY correction_date DESC
            """)
        
        corrections = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return corrections
    
    def add_correction(
        self,
        well_id: Optional[str],
        field_name: str,
        incorrect_value: str,
        correct_value: str,
        correction_reason: str,
        corrected_by: str,
        correction_source: str = "chat"
    ) -> str:
        """Add a new correction."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        correction_id = f"CORR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        correction_date = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO user_corrections (
                correction_id,
                well_id,
                field_name,
                incorrect_value,
                correct_value,
                correction_reason,
                corrected_by,
                correction_date,
                correction_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            correction_id,
            well_id,
            field_name,
            incorrect_value,
            correct_value,
            correction_reason,
            corrected_by,
            correction_date,
            correction_source
        ))
        
        conn.commit()
        conn.close()
        
        return correction_id
    
    def get_correction_stats(self) -> Dict[str, Any]:
        """Get statistics about corrections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Total corrections
        cursor.execute("SELECT COUNT(*) as total FROM user_corrections")
        total = cursor.fetchone()["total"]
        
        # By user
        cursor.execute("""
            SELECT corrected_by, COUNT(*) as count
            FROM user_corrections
            GROUP BY corrected_by
            ORDER BY count DESC
            LIMIT 5
        """)
        by_user = [dict(row) for row in cursor.fetchall()]
        
        # By field
        cursor.execute("""
            SELECT field_name, COUNT(*) as count
            FROM user_corrections
            GROUP BY field_name
            ORDER BY count DESC
            LIMIT 5
        """)
        by_field = [dict(row) for row in cursor.fetchall()]
        
        # Recent
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM user_corrections
            WHERE correction_date >= date('now', '-7 days')
        """)
        recent = cursor.fetchone()["count"]
        
        conn.close()
        
        return {
            "total_corrections": total,
            "recent_7_days": recent,
            "top_users": by_user,
            "top_fields": by_field
        }
    
    def search_corrections(
        self,
        query: str,
        well_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search corrections by content."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = """
            SELECT 
                correction_id,
                well_id,
                field_name,
                incorrect_value,
                correct_value,
                correction_reason,
                corrected_by,
                correction_date,
                correction_source
            FROM user_corrections
            WHERE (
                field_name LIKE ? 
                OR incorrect_value LIKE ? 
                OR correct_value LIKE ?
                OR correction_reason LIKE ?
            )
        """
        params = [f"%{query}%"] * 4
        
        if well_id:
            sql += " AND well_id = ?"
            params.append(well_id)
        
        if user_id:
            sql += " AND corrected_by = ?"
            params.append(user_id)
        
        sql += " ORDER BY correction_date DESC LIMIT 20"
        
        cursor.execute(sql, params)
        corrections = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return corrections
