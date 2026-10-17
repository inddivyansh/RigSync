#!/usr/bin/env python3
"""
Build ChromaDB vector embeddings for semantic search
"""
import chromadb
from chromadb.config import Settings
import re
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).parent.parent
CHROMA_PATH = BACKEND_DIR / "data" / "chroma"
SAMPLE_DATA = BACKEND_DIR.parent / "test-data" / "dataset"

def init_chromadb():
    """Initialize ChromaDB client"""
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client

def parse_manual_sections(manual_path):
    """Parse well-type manual into sections"""
    with open(manual_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    well_type = 'T200' if 'T200' in manual_path.name else 'T350'
    
    # Split by ## headers
    sections = []
    pattern = r'##\s+(\d+\.?\d*)\s+(.*?)\n(.*?)(?=\n##|\Z)'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        section_num = match.group(1)
        section_title = match.group(2).strip()
        section_text = match.group(3).strip()
        
        if section_text:
            sections.append({
                'id': f"manual_{well_type}_s{section_num}",
                'document': section_text,
                'metadata': {
                    'source_file': manual_path.name,
                    'well_type_code': well_type,
                    'section_number': section_num,
                    'section_title': section_title,
                    'doc_type': 'manual'
                }
            })
    
    return sections

def parse_sop_protocols(sop_path):
    """Parse SOP into protocol sections"""
    with open(sop_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sop_type = 'SR' if 'spill' in sop_path.name.lower() else 'RC'
    
    sections = []
    
    # Split by protocol IDs
    pattern = r'\*\*(' + sop_type + r'-\d+)\*\*\s+(.*?)(?=\*\*' + sop_type + r'-|\Z)'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        protocol_id = match.group(1)
        protocol_text = match.group(2).strip()
        
        if protocol_text:
            sections.append({
                'id': f"sop_{protocol_id}",
                'document': protocol_text,
                'metadata': {
                    'source_file': sop_path.name,
                    'protocol_id': protocol_id,
                    'doc_type': 'sop',
                    'category': 'spill_response' if sop_type == 'SR' else 'regulatory_compliance'
                }
            })
    
    return sections

def build_manual_embeddings(client):
    """Build embeddings for well-type manuals"""
    print("📝 Building manual embeddings...")
    
    # Create or get collection
    try:
        collection = client.get_collection("manuals")
        client.delete_collection("manuals")
    except:
        pass
    
    collection = client.create_collection(
        name="manuals",
        metadata={"description": "Well-type operating manuals"}
    )
    
    # Parse T200 manual
    t200_path = SAMPLE_DATA / "fleet" / "well-types" / "T200.md"
    t200_sections = parse_manual_sections(t200_path)
    print(f"   T200: {len(t200_sections)} sections")
    
    # Parse T350 manual
    t350_path = SAMPLE_DATA / "fleet" / "well-types" / "T350.md"
    t350_sections = parse_manual_sections(t350_path)
    print(f"   T350: {len(t350_sections)} sections")
    
    all_sections = t200_sections + t350_sections
    
    # Add to collection
    if all_sections:
        collection.add(
            ids=[s['id'] for s in all_sections],
            documents=[s['document'] for s in all_sections],
            metadatas=[s['metadata'] for s in all_sections]
        )
    
    print(f"   ✅ Indexed {len(all_sections)} manual sections")
    return len(all_sections)

def build_sop_embeddings(client):
    """Build embeddings for SOPs"""
    print("📝 Building SOP embeddings...")
    
    # Create or get collection
    try:
        collection = client.get_collection("sops")
        client.delete_collection("sops")
    except:
        pass
    
    collection = client.create_collection(
        name="sops",
        metadata={"description": "Standard Operating Procedures"}
    )
    
    # Parse spill response SOP
    spill_path = SAMPLE_DATA / "fleet" / "sops" / "spill-response-sop.md"
    spill_sections = parse_sop_protocols(spill_path)
    print(f"   Spill Response: {len(spill_sections)} protocols")
    
    # Parse regulatory compliance SOP
    reg_path = SAMPLE_DATA / "fleet" / "sops" / "regulatory-compliance-sop.md"
    reg_sections = parse_sop_protocols(reg_path)
    print(f"   Regulatory Compliance: {len(reg_sections)} protocols")
    
    all_sections = spill_sections + reg_sections
    
    # Add to collection
    if all_sections:
        collection.add(
            ids=[s['id'] for s in all_sections],
            documents=[s['document'] for s in all_sections],
            metadatas=[s['metadata'] for s in all_sections]
        )
    
    print(f"   ✅ Indexed {len(all_sections)} SOP protocols")
    return len(all_sections)

def build_report_embeddings(client):
    """Build embeddings for maintenance reports"""
    print("📝 Building maintenance report embeddings...")
    
    # Create or get collection
    try:
        collection = client.get_collection("reports")
        client.delete_collection("reports")
    except:
        pass
    
    collection = client.create_collection(
        name="reports",
        metadata={"description": "Maintenance reports"}
    )
    
    reports = []
    assets_dir = SAMPLE_DATA / "assets"
    
    for well_dir in sorted(assets_dir.iterdir()):
        if not well_dir.is_dir() or not well_dir.name.startswith('WELL-'):
            continue
        
        reports_dir = well_dir / "maintenance-reports"
        if not reports_dir.exists():
            continue
        
        for report_file in reports_dir.glob("*.md"):
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            maintenance_id = report_file.stem
            asset_id = well_dir.name
            
            reports.append({
                'id': f"report_{maintenance_id}",
                'document': content,
                'metadata': {
                    'source_file': str(report_file.relative_to(SAMPLE_DATA.parent)),
                    'asset_id': asset_id,
                    'maintenance_id': maintenance_id,
                    'doc_type': 'report'
                }
            })
        
        if len(reports) % 100 == 0 and reports:
            print(f"   Collected {len(reports)} reports...")
    
    # Add to collection in batches
    batch_size = 100
    for i in range(0, len(reports), batch_size):
        batch = reports[i:i+batch_size]
        collection.add(
            ids=[r['id'] for r in batch],
            documents=[r['document'] for r in batch],
            metadatas=[r['metadata'] for r in batch]
        )
        if (i + batch_size) % 500 == 0:
            print(f"   Indexed {i+batch_size} reports...")
    
    print(f"   ✅ Indexed {len(reports)} maintenance reports")
    return len(reports)

def build_context_embeddings(client):
    """Build embeddings for context notes"""
    print("📝 Building context note embeddings...")
    
    # Create or get collection
    try:
        collection = client.get_collection("context")
        client.delete_collection("context")
    except:
        pass
    
    collection = client.create_collection(
        name="context",
        metadata={"description": "Context notes and operator feedback"}
    )
    
    notes = []
    assets_dir = SAMPLE_DATA / "assets"
    
    import jsonlines
    
    for well_dir in sorted(assets_dir.iterdir()):
        if not well_dir.is_dir() or not well_dir.name.startswith('WELL-'):
            continue
        
        context_file = well_dir / "context.jsonl"
        if not context_file.exists():
            continue
        
        try:
            with jsonlines.open(context_file) as reader:
                for note in reader:
                    # Combine fields into searchable text
                    text = f"{note['note_type']}: {note['text']}"
                    
                    notes.append({
                        'id': f"context_{note['note_id']}",
                        'document': text,
                        'metadata': {
                            'asset_id': note['asset_id'],
                            'note_id': note['note_id'],
                            'note_type': note['note_type'],
                            'author_user_id': note['author_user_id'],
                            'created_at': note['created_at'],
                            'valid_from': note.get('valid_from'),
                            'valid_to': note.get('valid_to'),
                            'doc_type': 'context'
                        }
                    })
        except Exception as e:
            print(f"   ⚠️  Error reading context from {well_dir.name}: {e}")
            continue
    
    # Add to collection
    if notes:
        collection.add(
            ids=[n['id'] for n in notes],
            documents=[n['document'] for n in notes],
            metadatas=[n['metadata'] for n in notes]
        )
    
    print(f"   ✅ Indexed {len(notes)} context notes")
    return len(notes)

def build_embeddings():
    """Main function to build all embeddings"""
    print("🚀 Building ChromaDB embeddings...")
    print(f"📂 ChromaDB path: {CHROMA_PATH}")
    
    client = init_chromadb()
    
    manual_count = build_manual_embeddings(client)
    sop_count = build_sop_embeddings(client)
    report_count = build_report_embeddings(client)
    context_count = build_context_embeddings(client)
    
    print(f"\n📊 Embedding Summary:")
    print(f"   Manuals: {manual_count} sections")
    print(f"   SOPs: {sop_count} protocols")
    print(f"   Reports: {report_count} documents")
    print(f"   Context: {context_count} notes")
    print(f"   Total: {manual_count + sop_count + report_count + context_count} documents")
    
    # Verify collections
    print(f"\n✅ Collections created:")
    for coll in client.list_collections():
        print(f"   - {coll.name}: {coll.count()} documents")
    
    print("\n✅ Embeddings build complete")

if __name__ == "__main__":
    build_embeddings()
