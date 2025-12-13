"""
Combined Protein Database Query Demonstration

This script demonstrates comprehensive querying capabilities across both
MongoDB (document store) and Neo4j (graph database) for protein data analysis.

Usage:
    python combined_demo.py [protein_id]
"""

import sys
import os
import json
from typing import Dict, Any

# Add the search_queries directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mongo_queries import MongoProteinQueryManager
from neo4j_queries import Neo4jProteinQueryManager


class CombinedProteinQueryDemo:
    """Demonstration class showcasing both MongoDB and Neo4j query capabilities"""
    
    def __init__(self):
        self.mongo_manager = MongoProteinQueryManager()
        self.neo4j_manager = Neo4jProteinQueryManager()
        self.connected = False
    
    def connect_databases(self):
        """Connect to both databases"""
        try:
            print("🔗 Connecting to databases...")
            self.mongo_manager.connect()
            self.neo4j_manager.connect()
            self.connected = True
            print("✅ Successfully connected to both databases")
        except Exception as e:
            print(f"❌ Failed to connect to databases: {e}")
            return False
        return True
    
    def disconnect_databases(self):
        """Disconnect from both databases"""
        if self.connected:
            self.mongo_manager.disconnect()
            self.neo4j_manager.disconnect()
            self.connected = False
    
    def compare_protein_search(self, protein_id: str):
        """Compare search results between MongoDB and Neo4j for a specific protein"""
        
        print(f"\n{'='*80}")
        print(f"COMPARATIVE ANALYSIS FOR PROTEIN: {protein_id}")
        print(f"{'='*80}")
        
        # MongoDB search
        print("\n📄 MONGODB (Document Store) Results:")
        print("-" * 50)
        mongo_result = self.mongo_manager.search_by_identifier(protein_id)
        
        if mongo_result:
            print(f"  UniProt ID: {mongo_result.get('uniprot_id', 'N/A')}")
            print(f"  Entry Name: {mongo_result.get('entry_name', 'N/A')}")
            print(f"  Organism: {mongo_result.get('organism', 'N/A')}")
            print(f"  Protein Names: {', '.join(mongo_result.get('protein_names', [])) if mongo_result.get('protein_names') else 'N/A'}")
            print(f"  Sequence Length: {mongo_result.get('sequence', {}).get('length', 'N/A')}")
            print(f"  EC Numbers: {', '.join(mongo_result.get('ec_numbers', [])) if mongo_result.get('ec_numbers') else 'None'}")
            print(f"  InterPro Domains: {len(mongo_result.get('interpro_ids', []))}")
            print(f"  Is Labeled: {mongo_result.get('is_labelled', False)}")
        else:
            print("  ❌ Protein not found in MongoDB")
        
        # Neo4j search
        print("\n🕸️ NEO4J (Graph Database) Results:")
        print("-" * 50)
        neo4j_result = self.neo4j_manager.search_by_identifier(protein_id)
        
        if neo4j_result:
            print(f"  UniProt ID: {neo4j_result.get('uniprot_id', 'N/A')}")
            print(f"  Entry Name: {neo4j_result.get('entry_name', 'N/A')}")
            print(f"  Organism: {neo4j_result.get('organism', 'N/A')}")
            print(f"  Length: {neo4j_result.get('length', 'N/A')}")
            print(f"  EC Numbers: {', '.join(neo4j_result.get('ec_numbers', [])) if neo4j_result.get('ec_numbers') else 'None'}")
            print(f"  Is Labeled: {neo4j_result.get('is_labelled', False)}")
            
            # Get neighborhood information
            neighborhood = self.neo4j_manager.get_protein_neighborhood(protein_id, depth=1)
            print(f"  Direct Neighbors: {len(neighborhood.get('neighbors', []))}")
            print(f"  Connected Domains: {len(neighborhood.get('domains', []))}")
            print(f"  Similarity Relationships: {len(neighborhood.get('relationships', []))}")
            
            # Get neighbors of neighbors
            neighborhood_2 = self.neo4j_manager.get_protein_neighborhood(protein_id, depth=2)
            print(f"  Neighbors (depth 2): {len(neighborhood_2.get('neighbors', []))}")
            
        else:
            print("  ❌ Protein not found in Neo4j")
        
        return mongo_result, neo4j_result
    
    def demonstrate_search_capabilities(self):
        """Demonstrate various search capabilities"""
        
        print(f"\n{'='*80}")
        print("SEARCH CAPABILITIES DEMONSTRATION")
        print(f"{'='*80}")
        
        # 1. Search by name/description
        print("\n🔍 SEARCH BY NAME/DESCRIPTION:")
        print("-" * 40)
        
        search_term = "kinase"
        
        # MongoDB text search
        mongo_results = self.mongo_manager.search_by_description(search_term)
        print(f"MongoDB found {len(mongo_results)} proteins matching '{search_term}'")
        if mongo_results:
            for i, protein in enumerate(mongo_results[:3]):
                names = protein.get('protein_names', ['N/A'])
                print(f"  {i+1}. {protein.get('entry_name', 'N/A')} - {names[0] if names else 'N/A'}")
        
        # Neo4j name search
        neo4j_results = self.neo4j_manager.search_by_name_or_entry(search_term)
        print(f"Neo4j found {len(neo4j_results)} proteins matching '{search_term}'")
        if neo4j_results:
            for i, protein in enumerate(neo4j_results[:3]):
                print(f"  {i+1}. {protein.get('entry_name', 'N/A')} - {protein.get('uniprot_id', 'N/A')}")
    
    def compare_statistics(self):
        """Compare statistics between both databases"""
        
        print(f"\n{'='*80}")
        print("DATABASE STATISTICS COMPARISON")
        print(f"{'='*80}")
        
        # MongoDB statistics
        print("\n📄 MONGODB STATISTICS:")
        print("-" * 30)
        mongo_stats = self.mongo_manager.get_statistics()
        
        print(f"  Total Proteins: {mongo_stats.get('total_proteins', 0)}")
        print(f"  Labeled Proteins: {mongo_stats.get('labeled_proteins', 0)}")
        print(f"  Unlabeled Proteins: {mongo_stats.get('unlabeled_proteins', 0)}")
        print(f"  Proteins with Domains: {mongo_stats.get('proteins_with_domains', 0)}")
        print(f"  Average Sequence Length: {mongo_stats.get('avg_sequence_length', 0)}")
        
        if mongo_stats.get('top_organisms'):
            print("  Top Organisms:")
            for org, count in mongo_stats['top_organisms']:
                print(f"    - {org}: {count}")
        
        # Neo4j statistics
        print("\n🕸️ NEO4J STATISTICS:")
        print("-" * 30)
        neo4j_stats = self.neo4j_manager.get_graph_statistics()
        
        print(f"  Total Proteins: {neo4j_stats.get('total_proteins', 0)}")
        print(f"  Total Domains: {neo4j_stats.get('total_domains', 0)}")
        print(f"  Similarity Relationships: {neo4j_stats.get('total_similarities', 0)}")
        print(f"  Labeled Proteins: {neo4j_stats.get('labeled_proteins', 0)}")
        print(f"  Unlabeled Proteins: {neo4j_stats.get('unlabeled_proteins', 0)}")
        print(f"  Isolated Proteins: {neo4j_stats.get('isolated_proteins', 0)}")
        print(f"  Average Degree: {neo4j_stats.get('avg_degree', 0)}")
        print(f"  Max Degree: {neo4j_stats.get('max_degree', 0)}")
        
        if neo4j_stats.get('top_connected_proteins'):
            print("  Most Connected Proteins:")
            for protein_id, entry_name, degree in neo4j_stats['top_connected_proteins']:
                print(f"    - {protein_id} ({entry_name}): {degree} connections")
        
        return mongo_stats, neo4j_stats
    
    def demonstrate_graph_specific_queries(self):
        """Demonstrate graph-specific queries unique to Neo4j"""
        
        print(f"\n{'='*80}")
        print("GRAPH-SPECIFIC ANALYSIS (Neo4j Only)")
        print(f"{'='*80}")
        
        # 1. High similarity protein pairs
        print("\n🤝 HIGH SIMILARITY PROTEIN PAIRS:")
        print("-" * 40)
        similar_pairs = self.neo4j_manager.find_proteins_by_similarity_threshold(0.3)
        
        if similar_pairs:
            print(f"Found {len(similar_pairs)} protein pairs with Jaccard similarity ≥ 0.3")
            for i, (p1, p2, jaccard) in enumerate(similar_pairs[:5]):
                print(f"  {i+1}. {p1} ↔ {p2} (Jaccard: {jaccard:.3f})")
        else:
            print("No high-similarity pairs found with current threshold")
        
        # 2. Protein neighborhood analysis
        if similar_pairs:
            # Use first protein from similar pairs for neighborhood demo
            sample_protein = similar_pairs[0][0]
            
            print(f"\n🕸️ NEIGHBORHOOD ANALYSIS FOR {sample_protein}:")
            print("-" * 50)
            
            # Depth 1 neighborhood
            neighborhood_1 = self.neo4j_manager.get_protein_neighborhood(sample_protein, depth=1)
            if neighborhood_1:
                print(f"  Direct neighbors: {len(neighborhood_1['neighbors'])}")
                print(f"  Connected domains: {len(neighborhood_1['domains'])}")
                
                # Show some neighbor details
                for i, neighbor in enumerate(neighborhood_1['neighbors'][:3]):
                    print(f"    Neighbor {i+1}: {neighbor.get('entry_name', 'N/A')} ({neighbor.get('uniprot_id', 'N/A')})")
            
            # Depth 2 neighborhood
            neighborhood_2 = self.neo4j_manager.get_protein_neighborhood(sample_protein, depth=2)
            if neighborhood_2:
                print(f"  Extended neighbors (depth 2): {len(neighborhood_2['neighbors'])}")
    
    def generate_visualization_data(self, protein_id: str):
        """Generate visualization data for a protein neighborhood"""
        
        print(f"\n{'='*80}")
        print(f"VISUALIZATION DATA GENERATION FOR {protein_id}")
        print(f"{'='*80}")
        
        output_file = f"visualization_{protein_id}.json"
        viz_data = self.neo4j_manager.export_neighborhood_for_visualization(
            protein_id, depth=1, output_file=output_file
        )
        
        if viz_data:
            print(f"\n📊 VISUALIZATION SUMMARY:")
            print(f"  Total nodes: {len(viz_data.get('nodes', []))}")
            print(f"  Total edges: {len(viz_data.get('edges', []))}")
            print(f"  Center protein: {viz_data.get('center_protein', 'N/A')}")
            
            # Count node types
            node_types = {}
            for node in viz_data.get('nodes', []):
                node_type = node.get('type', 'unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            print(f"  Node types: {dict(node_types)}")
            print(f"  Visualization data saved to: {output_file}")
        
        return viz_data


def main():
    """Main demonstration function"""
    
    # Get protein ID from command line or use default
    protein_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    demo = CombinedProteinQueryDemo()
    
    try:
        # Connect to databases
        if not demo.connect_databases():
            print("❌ Cannot proceed without database connections")
            return
        
        print("\n🧬 COMPREHENSIVE PROTEIN DATABASE QUERY DEMONSTRATION")
        print("This demo showcases querying capabilities across MongoDB and Neo4j databases")
        
        # 1. Compare statistics
        demo.compare_statistics()
        
        # 2. Demonstrate search capabilities
        demo.demonstrate_search_capabilities()
        
        # 3. Graph-specific queries
        demo.demonstrate_graph_specific_queries()
        
        # 4. If protein ID provided, do detailed comparison
        if protein_id:
            demo.compare_protein_search(protein_id)
            demo.generate_visualization_data(protein_id)
        else:
            # Get a sample protein ID for demonstration
            with demo.neo4j_manager.driver.session() as session:
                result = session.run("MATCH (p:Protein) RETURN p.uniprot_id LIMIT 1")
                record = result.single()
                if record:
                    sample_id = record["p.uniprot_id"]
                    print(f"\n🔬 Using sample protein {sample_id} for detailed analysis...")
                    demo.compare_protein_search(sample_id)
                    demo.generate_visualization_data(sample_id)
        
        print(f"\n{'='*80}")
        print("✅ DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("This showcases the comprehensive querying capabilities")
        print("for both document-based and graph-based protein databases.")
        print(f"{'='*80}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Demonstration interrupted by user")
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
    finally:
        demo.disconnect_databases()


if __name__ == "__main__":
    main()