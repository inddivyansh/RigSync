#!/usr/bin/env python3
"""
Build NetworkX knowledge graph from well relationships
"""
import sqlite3
import json
import networkx as nx
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"
GRAPH_PATH = BACKEND_DIR / "data" / "graph" / "knowledge_graph.json"

def build_graph():
    """Build knowledge graph from database"""
    print("🚀 Building knowledge graph...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create directed graph
    G = nx.DiGraph()
    
    # Add area nodes
    print("📝 Adding areas...")
    cursor.execute("SELECT * FROM areas")
    areas = cursor.fetchall()
    for area in areas:
        G.add_node(area['area_id'], 
                   type='Area',
                   name=area['name'],
                   team_id=area['team_id'],
                   lat=area['center_lat'],
                   lon=area['center_lon'])
    print(f"   ✅ Added {len(areas)} areas")
    
    # Add team nodes
    print("📝 Adding teams...")
    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()
    for team in teams:
        G.add_node(team['team_id'],
                   type='Team',
                   name=team['name'],
                   lead_user_id=team['lead_user_id'])
    print(f"   ✅ Added {len(teams)} teams")
    
    # Add user nodes
    print("📝 Adding users...")
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    for user in users:
        G.add_node(user['user_id'],
                   type='User',
                   name=user['name'],
                   role=user['role'],
                   team_id=user['team_id'])
    print(f"   ✅ Added {len(users)} users")
    
    # Add well nodes
    print("📝 Adding wells...")
    cursor.execute("SELECT * FROM wells")
    wells = cursor.fetchall()
    for well in wells:
        G.add_node(well['asset_id'],
                   type='Well',
                   name=well['name'],
                   well_type=well['well_type'],
                   area_id=well['area_id'],
                   team_id=well['team_id'],
                   in_charge_user_id=well['in_charge_user_id'],
                   lat=well['lat'],
                   lon=well['lon'],
                   status=well['recorded_status'])
    print(f"   ✅ Added {len(wells)} wells")
    
    # Add equipment nodes
    print("📝 Adding equipment...")
    cursor.execute("SELECT * FROM equipment")
    equipment = cursor.fetchall()
    for equip in equipment:
        G.add_node(equip['equipment_id'],
                   type='Equipment',
                   kind=equip['kind'],
                   model=equip['model'],
                   asset_id=equip['asset_id'])
    print(f"   ✅ Added {len(equipment)} equipment")
    
    # Add edges
    print("📝 Adding relationships...")
    
    # Well → Area (belongs_to)
    for well in wells:
        G.add_edge(well['asset_id'], well['area_id'], relation='belongs_to')
    
    # Area → Team (managed_by)
    for area in areas:
        G.add_edge(area['area_id'], area['team_id'], relation='managed_by')
    
    # Team → User (has_member)
    for user in users:
        G.add_edge(user['team_id'], user['user_id'], relation='has_member')
    
    # User → Team (leads) - for team leads
    for team in teams:
        if team['lead_user_id']:
            G.add_edge(team['lead_user_id'], team['team_id'], relation='leads')
    
    # Well → User (in_charge)
    for well in wells:
        if well['in_charge_user_id']:
            G.add_edge(well['asset_id'], well['in_charge_user_id'], relation='in_charge')
    
    # Well → Equipment (has_component)
    for equip in equipment:
        G.add_edge(equip['asset_id'], equip['equipment_id'], relation='has_component')
    
    # Equipment → Equipment (connected_to) - create chain
    # Group equipment by asset
    cursor.execute("""
        SELECT asset_id, equipment_id, kind 
        FROM equipment 
        ORDER BY asset_id, 
        CASE kind 
            WHEN 'wellhead' THEN 1
            WHEN 'pump_jack' THEN 2
            WHEN 'rod_string' THEN 3
            WHEN 'downhole_pump' THEN 4
            WHEN 'flowline' THEN 5
            ELSE 6
        END
    """)
    equipment_list = cursor.fetchall()
    
    current_asset = None
    prev_equip = None
    for equip in equipment_list:
        if current_asset != equip['asset_id']:
            current_asset = equip['asset_id']
            prev_equip = None
        
        if prev_equip:
            G.add_edge(prev_equip, equip['equipment_id'], relation='connected_to')
        prev_equip = equip['equipment_id']
    
    print(f"   ✅ Added {G.number_of_edges()} relationships")
    
    # Build precomputed indexes
    print("📝 Building precomputed indexes...")
    
    # Well hierarchy
    well_hierarchy = {}
    for well in wells:
        area = [a for a in areas if a['area_id'] == well['area_id']][0]
        team = [t for t in teams if t['team_id'] == well['team_id']][0]
        in_charge = [u for u in users if u['user_id'] == well['in_charge_user_id']][0] if well['in_charge_user_id'] else None
        team_lead = [u for u in users if u['user_id'] == team['lead_user_id']][0] if team['lead_user_id'] else None
        
        well_equipment = [e for e in equipment if e['asset_id'] == well['asset_id']]
        
        well_hierarchy[well['asset_id']] = {
            'area': area['area_id'],
            'area_name': area['name'],
            'team': team['team_id'],
            'team_name': team['name'],
            'team_lead': team_lead['user_id'] if team_lead else None,
            'team_lead_name': team_lead['name'] if team_lead else None,
            'in_charge_user': in_charge['user_id'] if in_charge else None,
            'in_charge_name': in_charge['name'] if in_charge else None,
            'equipment': [{
                'equipment_id': e['equipment_id'],
                'kind': e['kind'],
                'model': e['model']
            } for e in well_equipment]
        }
    
    # Area wells
    area_wells = {}
    for area in areas:
        area_wells[area['area_id']] = [w['asset_id'] for w in wells if w['area_id'] == area['area_id']]
    
    # User wells
    user_wells = {}
    for user in users:
        user_wells[user['user_id']] = [w['asset_id'] for w in wells if w['in_charge_user_id'] == user['user_id']]
    
    print(f"   ✅ Created {len(well_hierarchy)} well hierarchies")
    print(f"   ✅ Created {len(area_wells)} area well lists")
    print(f"   ✅ Created {len(user_wells)} user well lists")
    
    # Export to JSON
    print("💾 Exporting to JSON...")
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    graph_data = nx.node_link_data(G)
    graph_data['indexes'] = {
        'well_hierarchy': well_hierarchy,
        'area_wells': area_wells,
        'user_wells': user_wells
    }
    
    with open(GRAPH_PATH, 'w') as f:
        json.dump(graph_data, f, indent=2)
    
    print(f"   ✅ Saved to {GRAPH_PATH}")
    
    print(f"\n📊 Graph Summary:")
    print(f"   Nodes: {G.number_of_nodes()}")
    print(f"   Edges: {G.number_of_edges()}")
    print(f"   Node types: {set(nx.get_node_attributes(G, 'type').values())}")
    print(f"   Edge types: {set(nx.get_edge_attributes(G, 'relation').values())}")
    
    print("\n✅ Knowledge graph build complete")
    
    conn.close()

if __name__ == "__main__":
    build_graph()
