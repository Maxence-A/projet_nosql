"""
Neo4j Query Module for Protein Graph Database

This module provides comprehensive querying functionality for the protein graph database.
It includes search capabilities, neighborhood exploration, and graph statistics.

Tasks implemented:
1. Search proteins by identifier, name, and/or description
2. View protein neighbors and neighbors of neighbors  
3. Compute graph statistics (isolated proteins, connectivity, etc.)
4. Visualization support for protein neighborhoods
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from neo4j import GraphDatabase, exceptions
import json


class Neo4jProteinQueryManager:
    """Manager class for querying protein graph data in Neo4j"""
    
    def __init__(self, neo4j_uri: str = None, user: str = None, password: str = None):
        """
        Initialize the Neo4j connection
        
        Args:
            neo4j_uri: Neo4j connection string
            user: Neo4j username
            password: Neo4j password
        """
        self.neo4j_uri = neo4j_uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self.driver = None
        
    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.user, self.password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✅ Connected to Neo4j at {self.neo4j_uri}")
        except exceptions.ServiceUnavailable as e:
            print(f"❌ Error connecting to Neo4j: {e}")
            raise
    
    def disconnect(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            print("🔌 Disconnected from Neo4j")
    
    def search_by_identifier(self, protein_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for a protein by its UniProt identifier
        
        Args:
            protein_id: UniProt identifier (e.g., 'P12345')
            
        Returns:
            Protein node properties or None if not found
        """
        query = """
        MATCH (p:Protein {uniprot_id: $protein_id})
        RETURN p
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, protein_id=protein_id)
                record = result.single()
                if record:
                    protein_data = dict(record["p"])
                    print(f"✅ Found protein with ID: {protein_id}")
                    return protein_data
                else:
                    print(f"❌ No protein found with ID: {protein_id}")
                    return None
        except Exception as e:
            print(f"❌ Error searching by identifier: {e}")
            return None
    
    def search_by_name_or_entry(self, search_term: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Search for proteins by name or entry name
        
        Args:
            search_term: Term to search in entry_name
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            List of matching protein nodes
        """
        if case_sensitive:
            query = """
            MATCH (p:Protein)
            WHERE p.entry_name CONTAINS $search_term
            RETURN p
            ORDER BY p.entry_name
            """
        else:
            query = """
            MATCH (p:Protein)
            WHERE toLower(p.entry_name) CONTAINS toLower($search_term)
            RETURN p
            ORDER BY p.entry_name
            """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, search_term=search_term)
                proteins = [dict(record["p"]) for record in result]
                print(f"✅ Found {len(proteins)} proteins matching: '{search_term}'")
                return proteins
        except Exception as e:
            print(f"❌ Error searching by name: {e}")
            return []
    
    def get_protein_neighborhood(self, protein_id: str, depth: int = 1) -> Dict[str, Any]:
        """
        Get protein and its neighborhood up to specified depth
        
        Args:
            protein_id: UniProt identifier
            depth: Neighborhood depth (1 = direct neighbors, 2 = neighbors of neighbors)
            
        Returns:
            Dictionary containing the protein, its neighbors, and relationships
        """
        if depth == 1:
            query = """
            MATCH (p:Protein {uniprot_id: $protein_id})
            OPTIONAL MATCH (p)-[r:SIMILAR]-(neighbor:Protein)
            OPTIONAL MATCH (p)-[:HAS_DOMAIN]->(d:Domain)
            RETURN p as center_protein,
                   collect(DISTINCT neighbor) as neighbors,
                   collect(DISTINCT r) as relationships,
                   collect(DISTINCT d) as domains
            """
        else:  # depth = 2
            query = """
            MATCH (p:Protein {uniprot_id: $protein_id})
            OPTIONAL MATCH path = (p)-[:SIMILAR*1..2]-(neighbor:Protein)
            WITH p, collect(DISTINCT neighbor) as all_neighbors
            OPTIONAL MATCH (p)-[r1:SIMILAR]-(n1:Protein)
            OPTIONAL MATCH (n1)-[r2:SIMILAR]-(n2:Protein)
            OPTIONAL MATCH (p)-[:HAS_DOMAIN]->(d:Domain)
            RETURN p as center_protein,
                   all_neighbors as neighbors,
                   collect(DISTINCT r1) + collect(DISTINCT r2) as relationships,
                   collect(DISTINCT d) as domains
            """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, protein_id=protein_id)
                record = result.single()
                
                if not record or not record["center_protein"]:
                    print(f"❌ Protein {protein_id} not found")
                    return {}
                
                neighborhood = {
                    "center_protein": dict(record["center_protein"]),
                    "neighbors": [dict(n) for n in record["neighbors"] if n is not None],
                    "relationships": [dict(r) for r in record["relationships"] if r is not None],
                    "domains": [dict(d) for d in record["domains"] if d is not None],
                    "depth": depth
                }
                
                print(f"✅ Found neighborhood for {protein_id}: {len(neighborhood['neighbors'])} neighbors at depth {depth}")
                return neighborhood
                
        except Exception as e:
            print(f"❌ Error getting neighborhood: {e}")
            return {}
    
    def get_protein_domains(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get all domains for a specific protein
        
        Args:
            protein_id: UniProt identifier
            
        Returns:
            List of domain nodes connected to the protein
        """
        query = """
        MATCH (p:Protein {uniprot_id: $protein_id})-[:HAS_DOMAIN]->(d:Domain)
        RETURN d
        ORDER BY d.interpro_id
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, protein_id=protein_id)
                domains = [dict(record["d"]) for record in result]
                print(f"✅ Found {len(domains)} domains for protein {protein_id}")
                return domains
        except Exception as e:
            print(f"❌ Error getting domains: {e}")
            return []
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Compute comprehensive graph statistics
        
        Returns:
            Dictionary containing various graph metrics
        """
        queries = {
            "total_proteins": "MATCH (p:Protein) RETURN count(p) as count",
            "total_domains": "MATCH (d:Domain) RETURN count(d) as count",
            "total_similarities": "MATCH ()-[r:SIMILAR]-() RETURN count(r)/2 as count",
            "labeled_proteins": "MATCH (p:Protein) WHERE p.is_labelled = true RETURN count(p) as count",
            "unlabeled_proteins": "MATCH (p:Protein) WHERE p.is_labelled = false RETURN count(p) as count",
        }
        
        # Query for isolated proteins (no SIMILAR relationships)
        isolated_query = """
        MATCH (p:Protein)
        WHERE NOT (p)-[:SIMILAR]-()
        RETURN count(p) as count
        """
        
        # Query for connectivity statistics
        degree_query = """
        MATCH (p:Protein)
        OPTIONAL MATCH (p)-[r:SIMILAR]-()
        WITH p, count(r) as degree
        RETURN avg(degree) as avg_degree, 
               max(degree) as max_degree,
               min(degree) as min_degree,
               stdev(degree) as std_degree
        """
        
        # Query for most connected proteins
        top_connected_query = """
        MATCH (p:Protein)-[r:SIMILAR]-()
        WITH p, count(r) as degree
        ORDER BY degree DESC
        LIMIT 5
        RETURN p.uniprot_id as protein_id, p.entry_name as entry_name, degree
        """
        
        # Query for domain statistics
        domain_stats_query = """
        MATCH (d:Domain)<-[:HAS_DOMAIN]-(p:Protein)
        WITH d, count(p) as protein_count
        RETURN avg(protein_count) as avg_proteins_per_domain,
               max(protein_count) as max_proteins_per_domain,
               min(protein_count) as min_proteins_per_domain
        """
        
        try:
            stats = {}
            
            with self.driver.session() as session:
                # Basic counts
                for stat_name, query in queries.items():
                    result = session.run(query)
                    record = result.single()
                    stats[stat_name] = record["count"] if record else 0
                
                # Isolated proteins
                result = session.run(isolated_query)
                record = result.single()
                stats["isolated_proteins"] = record["count"] if record else 0
                
                # Degree statistics
                result = session.run(degree_query)
                record = result.single()
                if record:
                    stats.update({
                        "avg_degree": round(record["avg_degree"] or 0, 2),
                        "max_degree": record["max_degree"] or 0,
                        "min_degree": record["min_degree"] or 0,
                        "std_degree": round(record["std_degree"] or 0, 2)
                    })
                
                # Top connected proteins
                result = session.run(top_connected_query)
                stats["top_connected_proteins"] = [
                    (record["protein_id"], record["entry_name"], record["degree"]) 
                    for record in result
                ]
                
                # Domain statistics
                result = session.run(domain_stats_query)
                record = result.single()
                if record:
                    stats.update({
                        "avg_proteins_per_domain": round(record["avg_proteins_per_domain"] or 0, 2),
                        "max_proteins_per_domain": record["max_proteins_per_domain"] or 0,
                        "min_proteins_per_domain": record["min_proteins_per_domain"] or 0
                    })
            
            print("✅ Graph statistics computed successfully")
            return stats
            
        except Exception as e:
            print(f"❌ Error computing statistics: {e}")
            return {}
    
    def find_proteins_by_similarity_threshold(self, min_jaccard: float = 0.3) -> List[Tuple[str, str, float]]:
        """
        Find protein pairs with similarity above threshold
        
        Args:
            min_jaccard: Minimum Jaccard coefficient threshold
            
        Returns:
            List of tuples (protein1_id, protein2_id, jaccard_score)
        """
        query = """
        MATCH (p1:Protein)-[r:SIMILAR]-(p2:Protein)
        WHERE r.jaccard_weight >= $min_jaccard AND id(p1) < id(p2)
        RETURN p1.uniprot_id as protein1, p2.uniprot_id as protein2, r.jaccard_weight as jaccard
        ORDER BY r.jaccard_weight DESC
        LIMIT 100
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, min_jaccard=min_jaccard)
                pairs = [(record["protein1"], record["protein2"], record["jaccard"]) for record in result]
                print(f"✅ Found {len(pairs)} protein pairs with Jaccard ≥ {min_jaccard}")
                return pairs
        except Exception as e:
            print(f"❌ Error finding similar proteins: {e}")
            return []
    
    def get_proteins_with_domain(self, domain_id: str) -> List[Dict[str, Any]]:
        """
        Get all proteins containing a specific InterPro domain
        
        Args:
            domain_id: InterPro domain identifier
            
        Returns:
            List of proteins containing the domain
        """
        query = """
        MATCH (d:Domain {interpro_id: $domain_id})<-[:HAS_DOMAIN]-(p:Protein)
        RETURN p
        ORDER BY p.uniprot_id
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, domain_id=domain_id)
                proteins = [dict(record["p"]) for record in result]
                print(f"✅ Found {len(proteins)} proteins with domain {domain_id}")
                return proteins
        except Exception as e:
            print(f"❌ Error searching by domain: {e}")
            return []
    
    def export_neighborhood_for_visualization(self, protein_id: str, depth: int = 1, 
                                           output_file: str = None) -> Dict[str, Any]:
        """
        Export protein neighborhood in format suitable for visualization
        
        Args:
            protein_id: UniProt identifier of center protein
            depth: Neighborhood depth
            output_file: Optional file to save JSON visualization data
            
        Returns:
            Visualization data structure
        """
        neighborhood = self.get_protein_neighborhood(protein_id, depth)
        
        if not neighborhood:
            return {}
        
        # Convert to visualization format (nodes and edges)
        viz_data = {
            "nodes": [],
            "edges": [],
            "center_protein": protein_id
        }
        
        # Add center protein node
        center = neighborhood["center_protein"]
        viz_data["nodes"].append({
            "id": center["uniprot_id"],
            "label": center.get("entry_name", center["uniprot_id"]),
            "type": "center",
            "is_labelled": center.get("is_labelled", False),
            "length": center.get("length", 0),
            "ec_numbers": center.get("ec_numbers", [])
        })
        
        # Add neighbor nodes
        for neighbor in neighborhood["neighbors"]:
            if neighbor["uniprot_id"] != protein_id:  # Avoid duplicating center
                viz_data["nodes"].append({
                    "id": neighbor["uniprot_id"],
                    "label": neighbor.get("entry_name", neighbor["uniprot_id"]),
                    "type": "neighbor",
                    "is_labelled": neighbor.get("is_labelled", False),
                    "length": neighbor.get("length", 0),
                    "ec_numbers": neighbor.get("ec_numbers", [])
                })
        
        # Add domain nodes
        for domain in neighborhood["domains"]:
            viz_data["nodes"].append({
                "id": f"domain_{domain['interpro_id']}",
                "label": domain["interpro_id"],
                "type": "domain"
            })
        
        # Add edges from relationships
        added_edges = set()
        for rel in neighborhood["relationships"]:
            # Get start and end node IDs from the relationship
            start_id = rel.get("start_node_id")  # This might need adjustment based on actual relationship structure
            end_id = rel.get("end_node_id")
            
            if start_id and end_id:
                edge_key = tuple(sorted([start_id, end_id]))
                if edge_key not in added_edges:
                    viz_data["edges"].append({
                        "from": start_id,
                        "to": end_id,
                        "type": "similarity",
                        "weight": rel.get("jaccard_weight", 0),
                        "shared_domains": rel.get("shared_domains", 0)
                    })
                    added_edges.add(edge_key)
        
        # Add domain edges (protein to domain)
        center_id = center["uniprot_id"]
        for domain in neighborhood["domains"]:
            viz_data["edges"].append({
                "from": center_id,
                "to": f"domain_{domain['interpro_id']}",
                "type": "has_domain"
            })
        
        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(viz_data, f, indent=2)
                print(f"✅ Visualization data saved to {output_file}")
            except Exception as e:
                print(f"❌ Error saving visualization data: {e}")
        
        return viz_data


def demo_neo4j_queries():
    """Demonstration of Neo4j query functionality"""
    
    # Initialize query manager
    query_manager = Neo4jProteinQueryManager()
    
    try:
        # Connect to database
        query_manager.connect()
        
        print("\n" + "="*60)
        print("NEO4J PROTEIN GRAPH QUERY DEMONSTRATION")
        print("="*60)
        
        # 1. Graph Statistics
        print("\n📊 GRAPH STATISTICS:")
        stats = query_manager.get_graph_statistics()
        for key, value in stats.items():
            if key == 'top_connected_proteins':
                print(f"  {key}:")
                for protein_id, entry_name, degree in value:
                    print(f"    - {protein_id} ({entry_name}): {degree} connections")
            else:
                print(f"  {key}: {value}")
        
        # 2. Search by identifier
        print("\n🔍 SEARCH BY IDENTIFIER:")
        # Get a sample protein ID for demo
        with query_manager.driver.session() as session:
            result = session.run("MATCH (p:Protein) RETURN p.uniprot_id LIMIT 1")
            record = result.single()
            if record:
                sample_id = record["p.uniprot_id"]
                protein = query_manager.search_by_identifier(sample_id)
                if protein:
                    print(f"  Found: {protein.get('entry_name', 'N/A')} (Length: {protein.get('length', 'N/A')})")
        
        # 3. Show neighborhood
        print("\n🕸️ PROTEIN NEIGHBORHOOD:")
        if 'sample_id' in locals():
            neighborhood = query_manager.get_protein_neighborhood(sample_id, depth=1)
            if neighborhood:
                print(f"  Center: {neighborhood['center_protein'].get('entry_name', 'N/A')}")
                print(f"  Neighbors: {len(neighborhood['neighbors'])}")
                print(f"  Domains: {len(neighborhood['domains'])}")
                print(f"  Similarity relationships: {len(neighborhood['relationships'])}")
        
        # 4. Isolated proteins
        print(f"\n🏝️ ISOLATION ANALYSIS:")
        isolated_count = stats.get('isolated_proteins', 0)
        total_count = stats.get('total_proteins', 0)
        if total_count > 0:
            isolation_rate = (isolated_count / total_count) * 100
            print(f"  Isolated proteins: {isolated_count} ({isolation_rate:.1f}%)")
            print(f"  Connected proteins: {total_count - isolated_count} ({100 - isolation_rate:.1f}%)")
        
        # 5. High similarity pairs
        print("\n🤝 HIGH SIMILARITY PAIRS:")
        similar_pairs = query_manager.find_proteins_by_similarity_threshold(0.5)
        for i, (p1, p2, jaccard) in enumerate(similar_pairs[:3]):
            print(f"  {i+1}. {p1} ↔ {p2} (Jaccard: {jaccard:.3f})")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
    finally:
        query_manager.disconnect()


if __name__ == "__main__":
    demo_neo4j_queries()