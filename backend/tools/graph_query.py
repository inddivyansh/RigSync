"""
Graph Query Tool - Traverse knowledge graph for relationships
"""
import json
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any

BACKEND_DIR = Path(__file__).parent.parent
GRAPH_PATH = BACKEND_DIR / "data" / "graph" / "knowledge_graph.json"

class GraphQueryTool:
    """Query well-area-team-user-equipment relationships"""
    
    def __init__(self):
        """Load graph and indexes"""
        if GRAPH_PATH.exists():
            with open(GRAPH_PATH, 'r') as f:
                graph_data = json.load(f)
            self.graph = nx.node_link_graph(graph_data)
            self.indexes = graph_data.get('indexes', {})
            self.well_hierarchy = self.indexes.get('well_hierarchy', {})
            self.area_wells = self.indexes.get('area_wells', {})
            self.user_wells = self.indexes.get('user_wells', {})
        else:
            self.graph = nx.DiGraph()
            self.indexes = {}
            self.well_hierarchy = {}
            self.area_wells = {}
            self.user_wells = {}
    
    def get_well_hierarchy(self, asset_id: str) -> Dict[str, Any]:
        """Get full hierarchy for a well"""
        return self.well_hierarchy.get(asset_id, {'error': f'Well {asset_id} not found'})
    
    def get_area_wells(self, area_id: str) -> List[str]:
        """Get all wells in an area"""
        return self.area_wells.get(area_id, [])
    
    def get_user_wells(self, user_id: str) -> List[str]:
        """Get wells a user is in charge of"""
        return self.user_wells.get(user_id, [])
    
    def get_neighbors(self, node_id: str, relation: str = None) -> List[Dict[str, Any]]:
        """
        Get neighboring nodes
        
        Args:
            node_id: Node identifier
            relation: Filter by relation type (optional)
            
        Returns:
            List of neighbor nodes with their attributes
        """
        if node_id not in self.graph:
            return [{'error': f'Node {node_id} not found'}]
        
        neighbors = []
        for successor in self.graph.successors(node_id):
            edge_data = self.graph.get_edge_data(node_id, successor)
            if relation and edge_data.get('relation') != relation:
                continue
            
            node_data = dict(self.graph.nodes[successor])
            node_data['node_id'] = successor
            node_data['relation'] = edge_data.get('relation')
            neighbors.append(node_data)
        
        return neighbors
    
    def traverse(
        self,
        start_node: str,
        relation: str,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Traverse graph following specific relation
        
        Args:
            start_node: Starting node
            relation: Relation to follow
            max_depth: Maximum depth to traverse
            
        Returns:
            List of reached nodes
        """
        if start_node not in self.graph:
            return [{'error': f'Node {start_node} not found'}]
        
        visited = []
        queue = [(start_node, 0)]
        seen = {start_node}
        
        while queue:
            node, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            for successor in self.graph.successors(node):
                edge_data = self.graph.get_edge_data(node, successor)
                if edge_data.get('relation') == relation and successor not in seen:
                    seen.add(successor)
                    node_data = dict(self.graph.nodes[successor])
                    node_data['node_id'] = successor
                    node_data['depth'] = depth + 1
                    visited.append(node_data)
                    queue.append((successor, depth + 1))
        
        return visited
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Pydantic schema for LLM function calling"""
        return {
            'name': 'graph_query',
            'description': 'Query well-area-team-user-equipment relationships. Use for "which wells in area X", "who is in charge of well Y", "get equipment for well Z".',
            'parameters': {
                'type': 'object',
                'properties': {
                    'operation': {
                        'type': 'string',
                        'enum': ['get_well_hierarchy', 'get_area_wells', 'get_user_wells', 'get_neighbors', 'traverse'],
                        'description': 'Operation to perform'
                    },
                    'node_id': {
                        'type': 'string',
                        'description': 'Node identifier (asset_id, area_id, user_id, etc.)'
                    },
                    'relation': {
                        'type': 'string',
                        'description': 'Relation type to filter/traverse (belongs_to, has_component, in_charge, etc.)',
                        'default': None
                    },
                    'max_depth': {
                        'type': 'integer',
                        'description': 'Maximum traversal depth',
                        'default': 2
                    }
                },
                'required': ['operation', 'node_id']
            }
        }

# Tool instance
graph_query_tool = GraphQueryTool()


def graph_query(query_type: str = "well_details", well_id: str = None, area: str = None, user_id: str = None, graph_path: str = None) -> Any:
    """Execute graph query helper function for agent."""
    tool = graph_query_tool
    if query_type in ("well_details", "get_well_hierarchy") and well_id:
        return tool.get_well_hierarchy(well_id)
    elif query_type == "get_area_wells" and area:
        return tool.get_area_wells(area)
    elif query_type == "get_user_wells" and user_id:
        return tool.get_user_wells(user_id)
    elif well_id:
        return tool.get_well_hierarchy(well_id)
    elif area:
        return tool.get_area_wells(area)
    elif user_id:
        return tool.get_user_wells(user_id)
    return {"error": "Invalid graph query parameters"}
