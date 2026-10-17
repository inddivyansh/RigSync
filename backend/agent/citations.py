"""
Citation tracking for RigSync agent responses.
Tracks sources from 7 different data types and formats them for transparency.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class SourceType(str, Enum):
    """Types of sources that can be cited."""
    DATABASE = "database"
    VECTOR = "vector"
    GRAPH = "graph"
    MEMORY = "memory"
    RULES = "rules"
    CALCULATION = "calculation"
    CONFLICT = "conflict"


@dataclass
class Citation:
    """A single citation with full provenance."""
    source_type: SourceType
    content: str
    metadata: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert citation to dictionary."""
        return {
            "source_type": self.source_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "confidence": self.confidence
        }
    
    def format_inline(self) -> str:
        """Format citation for inline display."""
        if self.source_type == SourceType.DATABASE:
            table = self.metadata.get("table", "unknown")
            return f"[DB:{table}]"
        
        elif self.source_type == SourceType.VECTOR:
            doc_type = self.metadata.get("document_type", "unknown")
            well_id = self.metadata.get("well_id", "unknown")
            return f"[DOC:{doc_type}:{well_id}]"
        
        elif self.source_type == SourceType.GRAPH:
            rel_type = self.metadata.get("relationship_type", "unknown")
            return f"[GRAPH:{rel_type}]"
        
        elif self.source_type == SourceType.MEMORY:
            corrected_by = self.metadata.get("corrected_by", "user")
            return f"[MEMORY:{corrected_by}]"
        
        elif self.source_type == SourceType.RULES:
            rule_id = self.metadata.get("rule_id", "unknown")
            return f"[RULE:{rule_id}]"
        
        elif self.source_type == SourceType.CALCULATION:
            calc_type = self.metadata.get("calculation_type", "unknown")
            return f"[CALC:{calc_type}]"
        
        elif self.source_type == SourceType.CONFLICT:
            severity = self.metadata.get("severity", "unknown")
            return f"[CONFLICT:{severity}]"
        
        return "[UNKNOWN]"
    
    def format_detailed(self) -> str:
        """Format citation with full details."""
        inline = self.format_inline()
        details = []
        
        if self.source_type == SourceType.DATABASE:
            table = self.metadata.get("table")
            query = self.metadata.get("query_summary")
            if table:
                details.append(f"Table: {table}")
            if query:
                details.append(f"Query: {query}")
        
        elif self.source_type == SourceType.VECTOR:
            doc_type = self.metadata.get("document_type")
            well_id = self.metadata.get("well_id")
            section = self.metadata.get("section")
            score = self.metadata.get("similarity_score")
            
            if doc_type:
                details.append(f"Document: {doc_type}")
            if well_id:
                details.append(f"Well: {well_id}")
            if section:
                details.append(f"Section: {section}")
            if score:
                details.append(f"Similarity: {score:.3f}")
        
        elif self.source_type == SourceType.GRAPH:
            from_node = self.metadata.get("from_node")
            to_node = self.metadata.get("to_node")
            rel_type = self.metadata.get("relationship_type")
            
            if from_node and to_node:
                details.append(f"Path: {from_node} → {to_node}")
            if rel_type:
                details.append(f"Relationship: {rel_type}")
        
        elif self.source_type == SourceType.MEMORY:
            corrected_by = self.metadata.get("corrected_by")
            correction_date = self.metadata.get("correction_date")
            
            if corrected_by:
                details.append(f"Corrected by: {corrected_by}")
            if correction_date:
                details.append(f"Date: {correction_date}")
        
        elif self.source_type == SourceType.RULES:
            rule_id = self.metadata.get("rule_id")
            rule_type = self.metadata.get("rule_type")
            category = self.metadata.get("category")
            
            if rule_id:
                details.append(f"Rule: {rule_id}")
            if rule_type:
                details.append(f"Type: {rule_type}")
            if category:
                details.append(f"Category: {category}")
        
        elif self.source_type == SourceType.CALCULATION:
            calc_type = self.metadata.get("calculation_type")
            inputs = self.metadata.get("inputs")
            formula = self.metadata.get("formula")
            
            if calc_type:
                details.append(f"Calculation: {calc_type}")
            if formula:
                details.append(f"Formula: {formula}")
            if inputs:
                details.append(f"Inputs: {inputs}")
        
        elif self.source_type == SourceType.CONFLICT:
            severity = self.metadata.get("severity")
            conflict_type = self.metadata.get("conflict_type")
            sources = self.metadata.get("conflicting_sources")
            
            if severity:
                details.append(f"Severity: {severity}")
            if conflict_type:
                details.append(f"Type: {conflict_type}")
            if sources:
                details.append(f"Sources: {', '.join(sources)}")
        
        if self.confidence:
            details.append(f"Confidence: {self.confidence:.2%}")
        
        if details:
            return f"{inline} {' | '.join(details)}"
        return inline


class CitationTracker:
    """Tracks and manages citations across agent execution."""
    
    def __init__(self):
        self.citations: List[Citation] = []
        self._citation_map: Dict[str, List[int]] = {}  # tool_call_id -> citation indices
    
    def add_citation(
        self,
        source_type: SourceType,
        content: str,
        metadata: Dict[str, Any],
        tool_call_id: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> Citation:
        """Add a citation and return it."""
        citation = Citation(
            source_type=source_type,
            content=content,
            metadata=metadata,
            confidence=confidence
        )
        
        idx = len(self.citations)
        self.citations.append(citation)
        
        if tool_call_id:
            if tool_call_id not in self._citation_map:
                self._citation_map[tool_call_id] = []
            self._citation_map[tool_call_id].append(idx)
        
        return citation
    
    def get_citations_for_tool(self, tool_call_id: str) -> List[Citation]:
        """Get all citations from a specific tool call."""
        indices = self._citation_map.get(tool_call_id, [])
        return [self.citations[i] for i in indices]
    
    def get_all_citations(self) -> List[Citation]:
        """Get all citations."""
        return self.citations
    
    def get_citations_by_type(self, source_type: SourceType) -> List[Citation]:
        """Get citations of a specific type."""
        return [c for c in self.citations if c.source_type == source_type]
    
    def format_summary(self, include_inline: bool = True) -> str:
        """Format a summary of all citations."""
        if not self.citations:
            return "No sources cited."
        
        # Group by source type
        by_type: Dict[SourceType, List[Citation]] = {}
        for citation in self.citations:
            if citation.source_type not in by_type:
                by_type[citation.source_type] = []
            by_type[citation.source_type].append(citation)
        
        lines = ["**Sources:**"]
        for source_type, citations in sorted(by_type.items(), key=lambda x: x[0].value):
            lines.append(f"\n{source_type.value.upper()} ({len(citations)}):")
            
            for i, citation in enumerate(citations[:5], 1):  # Show max 5 per type
                if include_inline:
                    lines.append(f"  {i}. {citation.format_detailed()}")
                else:
                    lines.append(f"  {i}. {citation.content[:100]}...")
            
            if len(citations) > 5:
                lines.append(f"  ... and {len(citations) - 5} more")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all citations to dictionary."""
        return {
            "citations": [c.to_dict() for c in self.citations],
            "count": len(self.citations),
            "by_type": {
                source_type.value: len(self.get_citations_by_type(source_type))
                for source_type in SourceType
            }
        }
    
    def clear(self):
        """Clear all citations."""
        self.citations.clear()
        self._citation_map.clear()


def create_db_citation(
    table: str,
    query_summary: str,
    content: str,
    row_count: Optional[int] = None,
    tool_call_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create database citation metadata."""
    metadata = {
        "table": table,
        "query_summary": query_summary
    }
    if row_count is not None:
        metadata["row_count"] = row_count
    
    return {
        "source_type": SourceType.DATABASE,
        "content": content,
        "metadata": metadata,
        "tool_call_id": tool_call_id
    }


def create_vector_citation(
    document_type: str,
    well_id: str,
    content: str,
    section: Optional[str] = None,
    similarity_score: Optional[float] = None,
    tool_call_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create vector search citation metadata."""
    metadata = {
        "document_type": document_type,
        "well_id": well_id
    }
    if section:
        metadata["section"] = section
    if similarity_score is not None:
        metadata["similarity_score"] = similarity_score
    
    return {
        "source_type": SourceType.VECTOR,
        "content": content,
        "metadata": metadata,
        "tool_call_id": tool_call_id,
        "confidence": similarity_score
    }


def create_graph_citation(
    from_node: str,
    to_node: str,
    relationship_type: str,
    content: str,
    tool_call_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create graph citation metadata."""
    return {
        "source_type": SourceType.GRAPH,
        "content": content,
        "metadata": {
            "from_node": from_node,
            "to_node": to_node,
            "relationship_type": relationship_type
        },
        "tool_call_id": tool_call_id
    }


def create_memory_citation(
    corrected_by: str,
    correction_date: str,
    content: str,
    well_id: Optional[str] = None,
    tool_call_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create memory citation metadata."""
    metadata = {
        "corrected_by": corrected_by,
        "correction_date": correction_date
    }
    if well_id:
        metadata["well_id"] = well_id
    
    return {
        "source_type": SourceType.MEMORY,
        "content": content,
        "metadata": metadata,
        "tool_call_id": tool_call_id
    }


def create_rule_citation(
    rule_id: str,
    rule_type: str,
    category: str,
    content: str,
    tool_call_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create rule citation metadata."""
    return {
        "source_type": SourceType.RULES,
        "content": content,
        "metadata": {
            "rule_id": rule_id,
            "rule_type": rule_type,
            "category": category
        },
        "tool_call_id": tool_call_id
    }


def create_calculation_citation(
    calculation_type: str,
    formula: str,
    inputs: str,
    content: str,
    tool_call_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create calculation citation metadata."""
    return {
        "source_type": SourceType.CALCULATION,
        "content": content,
        "metadata": {
            "calculation_type": calculation_type,
            "formula": formula,
            "inputs": inputs
        },
        "tool_call_id": tool_call_id
    }


def create_conflict_citation(
    severity: str,
    conflict_type: str,
    conflicting_sources: List[str],
    content: str,
    tool_call_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create conflict citation metadata."""
    return {
        "source_type": SourceType.CONFLICT,
        "content": content,
        "metadata": {
            "severity": severity,
            "conflict_type": conflict_type,
            "conflicting_sources": conflicting_sources
        },
        "tool_call_id": tool_call_id
    }
