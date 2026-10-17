"""
LangGraph-based agent orchestration for RigSync.
Implements agentic RAG with 6-node state machine: analyze → plan → execute → check conflicts → synthesize → finalize.
"""

import json
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from operator import add
from datetime import datetime

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Local imports
from agent.prompts import SYSTEM_PROMPT, get_tool_examples
from agent.schemas import QueryAnalysis, ToolCall, AgentResponse, ConflictAlert
from agent.citations import CitationTracker, SourceType
from memory.memory_manager import SessionManager, CorrectionTracker

# Tool imports
from tools.sql_query import execute_sql_query
from tools.vector_search import vector_search
from tools.graph_query import graph_query
from tools.downtime_calc import calculate_downtime
from tools.compliance_check import check_compliance
from tools.memory_retrieval import retrieve_memory
from tools.memory_update import update_memory
from tools.conflict_detect import detect_conflicts


class AgentState(TypedDict):
    """State for the agent graph."""
    # Input
    query: str
    session_id: str
    user_id: str
    
    # Analysis
    query_analysis: Optional[Dict[str, Any]]
    
    # Planning
    tool_plan: List[Dict[str, Any]]
    
    # Execution
    tool_results: Annotated[List[Dict[str, Any]], add]
    
    # Conflict checking
    conflicts: List[Dict[str, Any]]
    
    # Synthesis
    draft_response: Optional[str]
    citations: List[Dict[str, Any]]
    
    # Final
    final_response: Optional[str]
    metadata: Dict[str, Any]
    
    # Control
    errors: Annotated[List[str], add]
    iteration: int


class RigSyncAgent:
    """RigSync Agentic RAG Agent."""
    
    def __init__(
        self,
        db_path: str = "backend/data/db/oilwells.db",
        chroma_path: str = "backend/data/chroma",
        graph_path: str = "backend/data/graph/knowledge_graph.json",
        memory_dir: str = "backend/data/memory"
    ):
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.graph_path = graph_path
        
        # Initialize managers
        self.session_manager = SessionManager(memory_dir)
        self.correction_tracker = CorrectionTracker(db_path)
        
        # Build graph
        self.graph = self._build_graph()
        self.app = self.graph.compile()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("plan_tools", self._plan_tools)
        workflow.add_node("execute_tools", self._execute_tools)
        workflow.add_node("check_conflicts", self._check_conflicts)
        workflow.add_node("synthesize_response", self._synthesize_response)
        workflow.add_node("finalize", self._finalize)
        
        # Define edges
        workflow.set_entry_point("analyze_query")
        
        workflow.add_edge("analyze_query", "plan_tools")
        workflow.add_edge("plan_tools", "execute_tools")
        workflow.add_edge("execute_tools", "check_conflicts")
        
        # Conditional edge: if conflicts detected, might need re-execution
        workflow.add_conditional_edges(
            "check_conflicts",
            self._should_reexecute,
            {
                "reexecute": "execute_tools",
                "continue": "synthesize_response"
            }
        )
        
        workflow.add_edge("synthesize_response", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow
    
    def _analyze_query(self, state: AgentState) -> Dict[str, Any]:
        """Analyze the user query to understand intent."""
        query = state["query"]
        user_id = state["user_id"]
        
        # Extract intent signals
        analysis = {
            "intent_type": self._classify_intent(query),
            "entities": self._extract_entities(query),
            "time_context": self._extract_time_context(query),
            "requires_calculation": any(kw in query.lower() for kw in ["downtime", "production", "calculate", "how long"]),
            "requires_compliance": any(kw in query.lower() for kw in ["compliance", "violation", "overdue", "regulation", "sop"]),
            "requires_semantic_search": not any(kw in query.lower() for kw in ["list all", "count", "show me all"]),
            "correction_intent": any(kw in query.lower() for kw in ["actually", "correction", "wrong", "mistake"])
        }
        
        return {"query_analysis": analysis}
    
    def _classify_intent(self, query: str) -> str:
        """Classify query intent."""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["downtime", "production status", "non-producing"]):
            return "downtime_analysis"
        elif any(kw in query_lower for kw in ["compliance", "violation", "overdue", "inspection"]):
            return "compliance_check"
        elif any(kw in query_lower for kw in ["who", "team", "operator", "engineer"]):
            return "personnel_query"
        elif any(kw in query_lower for kw in ["maintenance", "repair", "issue", "problem"]):
            return "maintenance_query"
        elif any(kw in query_lower for kw in ["history", "past", "previous", "trend"]):
            return "historical_analysis"
        elif any(kw in query_lower for kw in ["correction", "wrong", "actually"]):
            return "correction"
        else:
            return "general_query"
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from query."""
        entities = {
            "well_ids": [],
            "areas": [],
            "users": [],
            "dates": []
        }
        
        # Simple pattern matching (could be enhanced with NER)
        import re
        
        # Extract WELL-XXXX patterns
        well_pattern = r'WELL-\d{4}'
        entities["well_ids"] = re.findall(well_pattern, query, re.IGNORECASE)
        
        # Extract area mentions
        area_keywords = ["north", "south", "east", "west", "field"]
        for keyword in area_keywords:
            if keyword in query.lower():
                entities["areas"].append(keyword.capitalize())
        
        return entities
    
    def _extract_time_context(self, query: str) -> Optional[str]:
        """Extract time context from query."""
        query_lower = query.lower()
        
        if "today" in query_lower:
            return "today"
        elif "this week" in query_lower:
            return "this_week"
        elif "this month" in query_lower:
            return "this_month"
        elif "last" in query_lower:
            return "last_period"
        
        return None
    
    def _plan_tools(self, state: AgentState) -> Dict[str, Any]:
        """Plan which tools to use based on analysis."""
        analysis = state["query_analysis"]
        query = state["query"]
        user_id = state["user_id"]
        
        tool_plan = []
        
        # 1. Always retrieve memory first to check for corrections
        tool_plan.append({
            "tool": "memory_retrieval",
            "params": {"user_id": user_id},
            "reason": "Check for user corrections and preferences"
        })
        
        # 2. If semantic search needed, use vector search
        if analysis["requires_semantic_search"]:
            tool_plan.append({
                "tool": "vector_search",
                "params": {"query": query, "top_k": 5},
                "reason": "Find relevant documents semantically"
            })
        
        # 3. If specific entities mentioned, use graph query
        if analysis["entities"]["well_ids"]:
            for well_id in analysis["entities"]["well_ids"]:
                tool_plan.append({
                    "tool": "graph_query",
                    "params": {"query_type": "well_details", "well_id": well_id},
                    "reason": f"Get relationships for {well_id}"
                })
        
        # 4. If downtime/production query, use downtime calculator
        if analysis["requires_calculation"]:
            if analysis["entities"]["well_ids"]:
                for well_id in analysis["entities"]["well_ids"]:
                    tool_plan.append({
                        "tool": "downtime_calc",
                        "params": {"well_id": well_id},
                        "reason": f"Calculate production status for {well_id}"
                    })
        
        # 5. If compliance query, use compliance checker
        if analysis["requires_compliance"]:
            if analysis["entities"]["well_ids"]:
                for well_id in analysis["entities"]["well_ids"]:
                    tool_plan.append({
                        "tool": "compliance_check",
                        "params": {"well_id": well_id},
                        "reason": f"Check compliance violations for {well_id}"
                    })
            else:
                # Check all wells
                tool_plan.append({
                    "tool": "compliance_check",
                    "params": {},
                    "reason": "Check compliance across all wells"
                })
        
        # 6. Use SQL for structured data queries
        if not analysis["requires_semantic_search"] or "all" in query.lower():
            # Generate SQL based on intent
            sql_query = self._generate_sql_from_intent(analysis, query)
            if sql_query:
                tool_plan.append({
                    "tool": "sql_query",
                    "params": {"query": sql_query},
                    "reason": "Fetch structured data"
                })
        
        # 7. If correction intent, prepare for memory update
        if analysis["correction_intent"]:
            # Will be handled in finalize after synthesis
            pass
        
        return {"tool_plan": tool_plan}
    
    def _generate_sql_from_intent(self, analysis: Dict[str, Any], query: str) -> Optional[str]:
        """Generate SQL query based on intent."""
        intent = analysis["intent_type"]
        
        if intent == "personnel_query":
            return "SELECT user_id, name, role, team FROM users"
        elif intent == "compliance_check":
            return "SELECT well_id, last_inspection_date, last_maintenance_date FROM wells"
        elif "list" in query.lower() and "well" in query.lower():
            return "SELECT well_id, well_type, status, area FROM wells"
        
        return None
    
    def _execute_tools(self, state: AgentState) -> Dict[str, Any]:
        """Execute planned tools."""
        tool_plan = state["tool_plan"]
        tool_results = []
        
        for plan_item in tool_plan:
            tool_name = plan_item["tool"]
            params = plan_item["params"]
            
            try:
                if tool_name == "sql_query":
                    result = execute_sql_query(params["query"], self.db_path)
                
                elif tool_name == "vector_search":
                    result = vector_search(
                        params["query"],
                        top_k=params.get("top_k", 5),
                        chroma_path=self.chroma_path
                    )
                
                elif tool_name == "graph_query":
                    result = graph_query(
                        params["query_type"],
                        params.get("well_id"),
                        params.get("area"),
                        params.get("user_id"),
                        self.graph_path
                    )
                
                elif tool_name == "downtime_calc":
                    result = calculate_downtime(params["well_id"], self.db_path)
                
                elif tool_name == "compliance_check":
                    result = check_compliance(
                        params.get("well_id"),
                        self.db_path
                    )
                
                elif tool_name == "memory_retrieval":
                    result = retrieve_memory(
                        params.get("user_id"),
                        params.get("well_id"),
                        params.get("field_name"),
                        self.db_path
                    )
                
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                
                tool_results.append({
                    "tool": tool_name,
                    "params": params,
                    "result": result,
                    "reason": plan_item["reason"]
                })
            
            except Exception as e:
                tool_results.append({
                    "tool": tool_name,
                    "params": params,
                    "error": str(e),
                    "reason": plan_item["reason"]
                })
        
        return {"tool_results": tool_results}
    
    def _check_conflicts(self, state: AgentState) -> Dict[str, Any]:
        """Check for conflicts in tool results."""
        tool_results = state["tool_results"]
        conflicts = []
        
        # Extract data points from tool results
        data_points = []
        for result in tool_results:
            if "result" in result and isinstance(result["result"], dict):
                data_points.append({
                    "source": result["tool"],
                    "data": result["result"]
                })
        
        # Run conflict detection if we have multiple sources
        if len(data_points) >= 2:
            try:
                conflict_result = detect_conflicts(data_points, self.db_path)
                if conflict_result.get("conflicts"):
                    conflicts = conflict_result["conflicts"]
            except Exception as e:
                # Log but don't fail
                print(f"Conflict detection error: {e}")
        
        return {"conflicts": conflicts}
    
    def _should_reexecute(self, state: AgentState) -> str:
        """Decide if we should re-execute tools due to conflicts."""
        conflicts = state["conflicts"]
        iteration = state.get("iteration", 0)
        
        # If high-severity conflicts and first iteration, might want to re-execute
        high_severity = [c for c in conflicts if c.get("severity") == "high"]
        
        if high_severity and iteration < 1:
            # For now, continue - in production could add resolution logic
            return "continue"
        
        return "continue"
    
    def _synthesize_response(self, state: AgentState) -> Dict[str, Any]:
        """Synthesize final response from tool results."""
        query = state["query"]
        tool_results = state["tool_results"]
        conflicts = state["conflicts"]
        
        # Build citation tracker
        citation_tracker = CitationTracker()
        
        # Synthesize response parts
        response_parts = []
        
        # Add main findings
        for result in tool_results:
            if "result" in result:
                tool_name = result["tool"]
                data = result["result"]
                
                # Format based on tool type
                if tool_name == "downtime_calc":
                    response_parts.append(self._format_downtime_result(data, citation_tracker))
                
                elif tool_name == "compliance_check":
                    response_parts.append(self._format_compliance_result(data, citation_tracker))
                
                elif tool_name == "vector_search":
                    response_parts.append(self._format_vector_result(data, citation_tracker))
                
                elif tool_name == "sql_query":
                    response_parts.append(self._format_sql_result(data, citation_tracker))
                
                elif tool_name == "memory_retrieval":
                    # Memory is used for context, not direct response
                    if data.get("corrections"):
                        citation_tracker.add_citation(
                            SourceType.MEMORY,
                            f"{len(data['corrections'])} user corrections found",
                            {"correction_count": len(data["corrections"])}
                        )
        
        # Add conflict warnings
        if conflicts:
            response_parts.append(self._format_conflicts(conflicts, citation_tracker))
        
        # Combine parts
        draft_response = "\n\n".join(response_parts)
        
        return {
            "draft_response": draft_response,
            "citations": citation_tracker.to_dict()
        }
    
    def _format_downtime_result(self, data: Dict[str, Any], tracker: CitationTracker) -> str:
        """Format downtime calculation result."""
        well_id = data.get("well_id", "Unknown")
        status = data.get("production_status", "unknown")
        downtime_days = data.get("downtime_days", 0)
        
        tracker.add_citation(
            SourceType.CALCULATION,
            f"Downtime calculation for {well_id}",
            {
                "calculation_type": "downtime",
                "formula": data.get("calculation_details", ""),
                "inputs": f"status={status}, days={downtime_days}"
            }
        )
        
        if status == "non-producing":
            return f"**{well_id}** is currently **non-producing** with **{downtime_days} days** of downtime."
        else:
            return f"**{well_id}** is currently **{status}**."
    
    def _format_compliance_result(self, data: Dict[str, Any], tracker: CitationTracker) -> str:
        """Format compliance check result."""
        violations = data.get("violations", [])
        
        if not violations:
            return "✅ No compliance violations found."
        
        lines = [f"⚠️ **{len(violations)} compliance violation(s) detected:**\n"]
        
        for v in violations[:5]:  # Show top 5
            well_id = v.get("well_id", "Unknown")
            rule_id = v.get("rule_id", "Unknown")
            severity = v.get("severity", "medium")
            message = v.get("message", "")
            
            tracker.add_citation(
                SourceType.RULES,
                f"Violation: {rule_id} on {well_id}",
                {
                    "rule_id": rule_id,
                    "rule_type": "compliance",
                    "category": severity
                }
            )
            
            lines.append(f"- **{well_id}**: {message} ({rule_id}, {severity})")
        
        if len(violations) > 5:
            lines.append(f"\n... and {len(violations) - 5} more violations.")
        
        return "\n".join(lines)
    
    def _format_vector_result(self, data: Dict[str, Any], tracker: CitationTracker) -> str:
        """Format vector search result."""
        results = data.get("results", [])
        
        if not results:
            return "No relevant documents found."
        
        lines = ["**Relevant information:**\n"]
        
        for r in results[:3]:  # Show top 3
            content = r.get("content", "")[:200]
            metadata = r.get("metadata", {})
            
            tracker.add_citation(
                SourceType.VECTOR,
                content,
                metadata,
                confidence=r.get("score")
            )
            
            lines.append(f"- {content}...")
        
        return "\n".join(lines)
    
    def _format_sql_result(self, data: Dict[str, Any], tracker: CitationTracker) -> str:
        """Format SQL query result."""
        rows = data.get("rows", [])
        
        if not rows:
            return "No matching records found."
        
        tracker.add_citation(
            SourceType.DATABASE,
            f"Found {len(rows)} records",
            {
                "table": "wells",
                "query_summary": "SELECT query",
                "row_count": len(rows)
            }
        )
        
        # Simple table formatting
        if len(rows) <= 5:
            return f"Found {len(rows)} records."
        else:
            return f"Found {len(rows)} records (showing summary)."
    
    def _format_conflicts(self, conflicts: List[Dict[str, Any]], tracker: CitationTracker) -> str:
        """Format conflict alerts."""
        lines = ["\n⚠️ **Data conflicts detected:**\n"]
        
        for conflict in conflicts[:3]:
            severity = conflict.get("severity", "low")
            message = conflict.get("message", "")
            sources = conflict.get("sources", [])
            
            tracker.add_citation(
                SourceType.CONFLICT,
                message,
                {
                    "severity": severity,
                    "conflict_type": "data_mismatch",
                    "conflicting_sources": sources
                }
            )
            
            lines.append(f"- [{severity.upper()}] {message}")
        
        return "\n".join(lines)
    
    def _finalize(self, state: AgentState) -> Dict[str, Any]:
        """Finalize response and update session."""
        draft_response = state["draft_response"]
        citations = state["citations"]
        session_id = state["session_id"]
        
        # Add citation summary
        citation_count = citations.get("count", 0)
        citation_summary = f"\n\n---\n*Response based on {citation_count} sources*"
        
        final_response = draft_response + citation_summary
        
        # Save to session
        self.session_manager.add_message(session_id, "assistant", final_response)
        
        metadata = {
            "citations": citations,
            "tool_count": len(state["tool_results"]),
            "conflict_count": len(state["conflicts"]),
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "final_response": final_response,
            "metadata": metadata
        }
    
    async def query(
        self,
        query: str,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Execute a query through the agent."""
        # Initialize state
        initial_state = {
            "query": query,
            "session_id": session_id,
            "user_id": user_id,
            "query_analysis": None,
            "tool_plan": [],
            "tool_results": [],
            "conflicts": [],
            "draft_response": None,
            "citations": [],
            "final_response": None,
            "metadata": {},
            "errors": [],
            "iteration": 0
        }
        
        # Save user message
        self.session_manager.add_message(session_id, "user", query)
        
        # Execute graph
        result = await self.app.ainvoke(initial_state)
        
        return {
            "response": result["final_response"],
            "metadata": result["metadata"]
        }
    
    def query_sync(
        self,
        query: str,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Synchronous version of query."""
        # Initialize state
        initial_state = {
            "query": query,
            "session_id": session_id,
            "user_id": user_id,
            "query_analysis": None,
            "tool_plan": [],
            "tool_results": [],
            "conflicts": [],
            "draft_response": None,
            "citations": [],
            "final_response": None,
            "metadata": {},
            "errors": [],
            "iteration": 0
        }
        
        # Save user message
        self.session_manager.add_message(session_id, "user", query)
        
        # Execute graph synchronously
        result = self.app.invoke(initial_state)
        
        return {
            "response": result["final_response"],
            "metadata": result["metadata"]
        }
