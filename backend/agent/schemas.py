"""
Pydantic schemas for agent I/O
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QueryAnalysis(BaseModel):
    """Parsed user query"""
    intent: str = Field(description="Query intent: status_check, trend_analysis, compliance_audit, downtime_report, correction_request, multi_well_comparison")
    entities: List[str] = Field(default_factory=list, description="Extracted entities: well IDs, area names, dates")
    temporal_scope: Optional[str] = Field(default=None, description="Date range or temporal context")
    requires_tools: List[str] = Field(default_factory=list, description="Tools needed to answer query")

class ToolCall(BaseModel):
    """Tool execution request"""
    tool_name: str = Field(description="Name of tool to call")
    parameters: Dict[str, Any] = Field(description="Parameters for tool")
    reasoning: Optional[str] = Field(default=None, description="Why this tool is needed")

class AgentResponse(BaseModel):
    """Final agent response"""
    answer: str = Field(description="Natural language answer")
    citations: List[str] = Field(default_factory=list, description="Source citations")
    visualization_type: Optional[str] = Field(default=None, description="Suggested visualization: status_card, table, line_chart, bar_chart, map, heatmap")
    visualization_data: Optional[Dict[str, Any]] = Field(default=None, description="Data for visualization")
    confidence: float = Field(default=1.0, description="Confidence in answer (0-1)")
    conflicts: Optional[List[Dict[str, Any]]] = Field(default=None, description="Detected conflicts if any")

class MemoryCorrection(BaseModel):
    """Data correction record"""
    user_id: str
    asset_id: str
    field: str
    old_value: Any
    new_value: Any
    reason: str
    scope: str = 'well'

class ConflictAlert(BaseModel):
    """Conflict between data sources"""
    conflict_type: str = Field(description="Type of conflict")
    source: str = Field(description="Conflicting source")
    existing_value: Any
    new_value: Any
    severity: str = Field(description="high, medium, or low")
    recommendation: Optional[str] = Field(default=None, description="How to resolve")
