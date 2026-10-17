"""
Vector Search Tool - Semantic search in ChromaDB collections
"""
import chromadb
from pathlib import Path
from typing import List, Dict, Any

BACKEND_DIR = Path(__file__).parent.parent
CHROMA_PATH = BACKEND_DIR / "data" / "chroma"

class VectorSearchTool:
    """Semantic search in manuals, SOPs, reports, and context notes"""
    
    COLLECTIONS = ['manuals', 'sops', 'reports', 'context']
    
    def __init__(self):
        """Initialize ChromaDB client"""
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    
    def _format_citation(self, metadata: Dict[str, Any]) -> str:
        """Format citation string from metadata"""
        doc_type = metadata.get('doc_type', '')
        
        if doc_type == 'manual':
            well_type = metadata.get('well_type_code', '')
            section = metadata.get('section_number', '')
            return f"[{well_type} Manual §{section}]"
        
        elif doc_type == 'sop':
            protocol_id = metadata.get('protocol_id', '')
            return f"[SOP §{protocol_id}]"
        
        elif doc_type == 'report':
            maintenance_id = metadata.get('maintenance_id', '')
            return f"[{maintenance_id} Report]"
        
        elif doc_type == 'context':
            author = metadata.get('author_user_id', '')
            date = metadata.get('created_at', '')[:10] if metadata.get('created_at') else ''
            return f"[Note by {author} on {date}]"
        
        return "[Unknown]"
    
    def search(
        self,
        query_text: str,
        collection_name: str,
        filter_metadata: Dict[str, Any] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents
        
        Args:
            query_text: Search query
            collection_name: Collection to search (manuals/sops/reports/context)
            filter_metadata: Metadata filters (e.g., {'asset_id': 'WELL-0001'})
            n_results: Number of results to return
            
        Returns:
            List of results with document, metadata, distance, citation
        """
        if collection_name not in self.COLLECTIONS:
            return [{
                'error': f"Invalid collection. Must be one of: {', '.join(self.COLLECTIONS)}"
            }]
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Build query
            where_filter = filter_metadata if filter_metadata else None
            
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter
            )
            
            # Format results
            formatted = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0
                    
                    formatted.append({
                        'document': results['documents'][0][i],
                        'metadata': metadata,
                        'distance': distance,
                        'citation': self._format_citation(metadata)
                    })
            
            return formatted
            
        except Exception as e:
            return [{'error': str(e)}]
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Pydantic schema for LLM function calling"""
        return {
            'name': 'vector_search',
            'description': 'Semantic search in well-type manuals, SOPs, maintenance reports, and context notes. Use to find relevant manual sections, compliance protocols, or similar maintenance cases.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query_text': {
                        'type': 'string',
                        'description': 'Natural language search query'
                    },
                    'collection_name': {
                        'type': 'string',
                        'enum': ['manuals', 'sops', 'reports', 'context'],
                        'description': 'Collection to search: manuals (T200/T350 docs), sops (SR/RC protocols), reports (maintenance reports), context (operator notes)'
                    },
                    'filter_metadata': {
                        'type': 'object',
                        'description': 'Metadata filters, e.g., {"asset_id": "WELL-0001"} to search only that well\'s reports',
                        'default': None
                    },
                    'n_results': {
                        'type': 'integer',
                        'description': 'Number of results to return',
                        'default': 5
                    }
                },
                'required': ['query_text', 'collection_name']
            }
        }

# Tool instance
vector_search_tool = VectorSearchTool()
