#!/usr/bin/env python3
"""Complete pipeline demonstration with a complex question."""
import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).resolve().parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from presearcher.init_pipeline import init_presearcher_agent
from utils.dataclass import PresearcherAgentRequest
from utils.logger import init_logger


async def main():
    logger = init_logger(name='complete_demo', log_dir='../../output/logs')
    
    print("\n" + "=" * 80)
    print("COMPLETE THREE-PHASE PIPELINE DEMONSTRATION")
    print("=" * 80)
    
    # Initialize agent
    print("\n⚙️  Initializing presearcher agent...")
    agent = init_presearcher_agent()
    print("✓ Agent initialized\n")
    
    # Create a complex request that will decompose
    request = PresearcherAgentRequest(
        topic='Should the USA adopt a universal basic income?',
        max_depth=2,           # Allow decomposition
        max_nodes=8,           # Allow multiple nodes
        max_subtasks=3,        # Up to 3 subtasks per node
        max_retriever_calls=1, # Keep searches quick for demo
        collect_graph=True,    # Collect full graph
    )
    
    print("📋 Research Question:")
    print(f"   {request.topic}")
    print(f"\n   Configuration:")
    print(f"   • max_depth: {request.max_depth}")
    print(f"   • max_nodes: {request.max_nodes}")
    print(f"   • max_subtasks: {request.max_subtasks}")
    print(f"   • max_retriever_calls: {request.max_retriever_calls}")
    
    print("\n" + "=" * 80)
    print("Starting pipeline... (this may take 5-10 minutes)")
    print("=" * 80 + "\n")
    
    # Run the full pipeline
    response = await agent.aforward(request)
    
    # Display results
    print("\n" + "=" * 80)
    print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    
    print(f"\n📊 FINAL RESULTS:")
    print(f"   • Report length: {len(response.writeup)} characters")
    print(f"   • Citations: {len(response.cited_documents)}")
    print(f"   • Graph nodes: {len(response.graph.nodes) if response.graph else 'N/A'}")
    
    if response.graph:
        print(f"\n🌳 DAG STRUCTURE:")
        print(f"   • Total nodes: {len(response.graph.nodes)}")
        print(f"   • Root node: {response.graph.root_id}")
        
        # Show node hierarchy
        def show_node(node_id, indent=0):
            node = response.graph.nodes[node_id]
            prefix = "   " + "  " * indent
            status_icon = "✓" if node.status == "complete" else "⏸️"
            print(f"{prefix}{status_icon} {node_id}: {node.question[:60]}...")
            print(f"{prefix}   Format: {node.expected_output_format}, Status: {node.status}")
            for child_id in node.children:
                show_node(child_id, indent + 1)
        
        print()
        show_node(response.graph.root_id)
    
    print(f"\n📄 FINAL REPORT (first 800 characters):")
    print("-" * 80)
    print(response.writeup[:800])
    if len(response.writeup) > 800:
        print("...")
        print(f"\n[Report continues for {len(response.writeup) - 800} more characters]")
    
    if response.cited_documents:
        print(f"\n📚 CITATIONS (showing first 5 of {len(response.cited_documents)}):")
        print("-" * 80)
        for i, doc in enumerate(response.cited_documents[:5], 1):
            title = doc.title[:60] if doc.title else "Untitled"
            print(f"   [{i}] {title}")
            print(f"       {doc.url[:70]}...")
    
    print("\n" + "=" * 80)
    print(f"✓ Complete results saved to: {logger.log_dir}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

