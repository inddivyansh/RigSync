"""
Test script for RigSync evaluation queries.
Based on the 18 evaluation queries from the hackathon guide.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.agent import RigSyncAgent
from memory.memory_manager import SessionManager


# Test queries from evaluation guide
EVALUATION_QUERIES = [
    # A1: Asking about the data
    {
        "id": "Q1",
        "query": "Is WELL-0001 producing oil right now? When was it last inspected, and by whom? Show me its status card.",
        "category": "single_well_status",
        "expected_facts": [
            "Not producing oil",
            "INS-0001-0203",
            "15 Oct 2026",
            "Ryan Brooks",
            "3.2 °C above air",
            "Below T200 limit",
            "Planned shut-in from 7 Oct",
            "Rod string replacement"
        ]
    },
    {
        "id": "Q2",
        "query": "Which wells in Northeast Block 8 are not producing oil right now, and why? Show them in a table.",
        "category": "area_query",
        "expected_facts": [
            "WELL-0164",
            "WELL-0170",
            "WELL-0172",
            "WELL-0175",
            "4 wells"
        ]
    },
    {
        "id": "Q3",
        "query": "Show a line chart of WELL-0001's wellhead temperature against air temperature for the last 13 weeks, and mark when it was not producing oil.",
        "category": "temporal_analysis",
        "expected_facts": [
            "13 readings",
            "23 Jul to 15 Oct 2026",
            "Not producing: 8 Oct and 15 Oct"
        ]
    },
    {
        "id": "Q4",
        "query": "How many oil spills has WELL-0001 had in the last 4 years, and how much oil in total? List them in a table.",
        "category": "historical_query",
        "expected_facts": [
            "6 spills",
            "15.1 barrels total",
            "7 detections (1 corrected as rainwater)"
        ]
    },
    {
        "id": "Q5",
        "query": "How many days was WELL-0001 down in 2025?",
        "category": "downtime_calculation",
        "expected_facts": [
            "21 days",
            "24 Jul 2025",
            "16 and 23 Oct 2025"
        ]
    },
    {
        "id": "Q6",
        "query": "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months? Show a bar chart.",
        "category": "comparative_analysis",
        "expected_facts": [
            "WELL-0121: 49 days",
            "WELL-0138: 42 days",
            "WELL-0107: 42 days"
        ]
    },
    {
        "id": "Q7",
        "query": "Show on a map every well in Northeast Block 8 with a real spill in the last 90 days.",
        "category": "geospatial",
        "expected_facts": [
            "4 wells",
            "WELL-0151",
            "WELL-0165",
            "WELL-0175",
            "WELL-0186"
        ]
    },
    {
        "id": "Q8",
        "query": "Show a heatmap of 2026 spills by geographic area and month.",
        "category": "aggregation",
        "expected_facts": [
            "Southwest Block 24: 43 spills",
            "Northeast Block 7: 37 spills",
            "Southwest Block 23: 35 spills",
            "Northeast Block 8: 26 spills"
        ]
    },
    {
        "id": "Q9",
        "query": "Which rules has WELL-0001 broken in the last 12 months, and what is still open?",
        "category": "compliance",
        "expected_facts": [
            "4 breaches",
            "11 Jun 2026 spill",
            "SR-01: reported after 41 hours",
            "SR-02: contained after 7 hours",
            "SR-03: cleanup verification overdue",
            "RC-04: response overdue",
            "USD 5,000 fine"
        ]
    },
    {
        "id": "Q10",
        "query": "In Southwest Block 24, which spills in the last 90 days were not contained within the SOP time limit?",
        "category": "compliance_analysis",
        "expected_facts": [
            "2 spills",
            "WELL-0082: 7.1 hours",
            "WELL-0100: 8.1 hours",
            "4-hour limit"
        ]
    },
    
    # A2: Memory and feedback
    {
        "id": "Q11",
        "query": "For the three wells we discussed yesterday, what have repairs cost this year?",
        "category": "memory",
        "expected_facts": [
            "WELL-0121: USD 25,794",
            "WELL-0138: USD 46,942",
            "WELL-0107: USD 5,176"
        ],
        "requires_context": "Q6"
    },
    {
        "id": "Q12",
        "query": "The 15 Oct reading for WELL-0164 is wrong. The handheld thermal gun used in that inspection was faulty; the field crew re-measured the wellhead at 41.0 °C.",
        "category": "correction",
        "expected_facts": [
            "Correction recorded",
            "INS-0164-0205",
            "41.0 °C vs 19.9 °C air",
            "21.1 °C warmer",
            "Above T200 limit",
            "WELL-0164 is producing oil",
            "Conflict with pump jack note"
        ]
    },
    {
        "id": "Q13",
        "query": "The AI estimated the 24 Sep spill at WELL-0151 as 4.5 bbl. The field crew measured 5.4 bbl.",
        "category": "correction_analysis",
        "expected_facts": [
            "Correction recorded",
            "INS-0151-0201",
            "5.4 bbl",
            "Reportable spill",
            "SR-01 breach: no report",
            "SR-02 breach: 6.4 hours",
            "SR-03: verification due 23 Nov 2026"
        ]
    },
    {
        "id": "Q14a",
        "query": "Which wells in Northeast Block 7 need a root-cause analysis on their pump jack?",
        "category": "maintenance_query",
        "expected_facts": [
            "WELL-0108",
            "WELL-0121",
            "WELL-0138",
            "3 repairs each"
        ]
    },
    {
        "id": "Q14b",
        "query": "Note for all T350 wells: our team now wants a pump jack root-cause analysis after 2 repairs, not 3.",
        "category": "rule_update",
        "expected_facts": [
            "Rule recorded for T350 wells",
            "2 repairs threshold"
        ]
    },
    
    # Part B: Several users
    {
        "id": "Q15a",
        "query": "Is WELL-0164 producing oil right now?",
        "category": "cross_user_correction",
        "expected_facts": [
            "Yes",
            "Corrected by Michael Turner",
            "41.0 °C",
            "Conflict with pump jack note"
        ],
        "user": "Jessica Reed"
    },
    {
        "id": "Q15b",
        "query": "Which spills in Northeast Block 8 in the last 90 days needed a report to the regulator?",
        "category": "cross_user_compliance",
        "expected_facts": [
            "WELL-0151",
            "5.4 bbl (corrected)",
            "No written notice",
            "Overdue"
        ],
        "user": "Laura Simmons"
    },
    {
        "id": "Q16a",
        "query": "FYI for everyone: WELL-0007 will be shut in from 17 Oct for a 10-day planned workover.",
        "category": "shared_note",
        "expected_facts": [
            "Note recorded",
            "Global scope"
        ],
        "user": "Jake Morales"
    }
]


async def run_test_query(agent: RigSyncAgent, query_info: dict, session_id: str, user_id: str):
    """Run a single test query and display results."""
    print(f"\n{'='*80}")
    print(f"Query {query_info['id']}: {query_info['category']}")
    print(f"{'='*80}")
    print(f"User: {user_id}")
    print(f"Question: {query_info['query']}")
    print(f"\nExpected facts:")
    for fact in query_info['expected_facts']:
        print(f"  - {fact}")
    
    print(f"\n{'-'*80}")
    print("Agent Response:")
    print(f"{'-'*80}")
    
    try:
        result = await agent.query(
            query=query_info['query'],
            session_id=session_id,
            user_id=user_id
        )
        
        print(result['response'])
        
        print(f"\n{'-'*80}")
        print("Metadata:")
        print(f"  Tools used: {result['metadata'].get('tool_count', 0)}")
        print(f"  Citations: {result['metadata'].get('citations', {}).get('count', 0)}")
        print(f"  Conflicts: {result['metadata'].get('conflict_count', 0)}")
        
        return result
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def run_all_tests(agent: RigSyncAgent):
    """Run all evaluation queries."""
    print("="*80)
    print("RigSync Evaluation Test Suite")
    print("="*80)
    print(f"Total queries: {len(EVALUATION_QUERIES)}")
    print()
    
    # Create sessions for different users
    users = {
        "Michael Turner": "user-michael-turner",
        "Jessica Reed": "user-jessica-reed",
        "Tyler Hughes": "user-tyler-hughes",
        "Jake Morales": "user-jake-morales",
        "Laura Simmons": "user-laura-simmons"
    }
    
    sessions = {}
    for name, user_id in users.items():
        session_id = f"session-{user_id}"
        agent.session_manager.create_session(session_id, user_id)
        sessions[name] = session_id
    
    # Run queries
    results = []
    for query_info in EVALUATION_QUERIES:
        # Determine user and session
        user_name = query_info.get("user", "Michael Turner")
        user_id = users.get(user_name, "user-michael-turner")
        session_id = sessions.get(user_name, "session-michael-turner")
        
        result = await run_test_query(agent, query_info, session_id, user_id)
        results.append({
            "query_id": query_info['id'],
            "success": result is not None,
            "result": result
        })
        
        # Small delay between queries
        await asyncio.sleep(0.5)
    
    # Summary
    print(f"\n{'='*80}")
    print("Test Summary")
    print(f"{'='*80}")
    successful = sum(1 for r in results if r['success'])
    print(f"Completed: {successful}/{len(results)}")
    print(f"Failed: {len(results) - successful}")
    
    failed = [r for r in results if not r['success']]
    if failed:
        print(f"\nFailed queries:")
        for r in failed:
            print(f"  - {r['query_id']}")


async def run_single_test(agent: RigSyncAgent, query_id: str):
    """Run a single query by ID."""
    query_info = next((q for q in EVALUATION_QUERIES if q['id'] == query_id), None)
    if not query_info:
        print(f"Query {query_id} not found")
        return
    
    user_name = query_info.get("user", "Michael Turner")
    user_id = f"user-{user_name.lower().replace(' ', '-')}"
    session_id = f"session-{user_id}"
    
    # Create session if needed
    if not agent.session_manager.get_session(session_id):
        agent.session_manager.create_session(session_id, user_id)
    
    await run_test_query(agent, query_info, session_id, user_id)


def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run RigSync evaluation queries")
    parser.add_argument(
        "--query",
        type=str,
        help="Run a single query by ID (e.g., Q1, Q2, etc.)"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="backend/data/db/oilwells.db",
        help="Path to database"
    )
    parser.add_argument(
        "--chroma-path",
        type=str,
        default="backend/data/chroma",
        help="Path to ChromaDB"
    )
    parser.add_argument(
        "--graph-path",
        type=str,
        default="backend/data/graph/knowledge_graph.json",
        help="Path to knowledge graph"
    )
    
    args = parser.parse_args()
    
    # Initialize agent
    print("Initializing RigSync agent...")
    agent = RigSyncAgent(
        db_path=args.db_path,
        chroma_path=args.chroma_path,
        graph_path=args.graph_path
    )
    print("✅ Agent initialized\n")
    
    # Run tests
    if args.query:
        asyncio.run(run_single_test(agent, args.query))
    else:
        asyncio.run(run_all_tests(agent))


if __name__ == "__main__":
    main()
