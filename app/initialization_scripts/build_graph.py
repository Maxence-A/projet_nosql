"""
Script optimisé pour construire le graphe Neo4j à partir des données MongoDB
en utilisant la librairie Graph Data Science (GDS) pour le calcul de similarité.
"""

import os
from pymongo import MongoClient
from neo4j import GraphDatabase

# ---------------------------
# CONFIG MONGO / NEO4J
# ---------------------------

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017") 
DB_NAME = "protein_db"
COLLECTION_NAME = "all_proteins"

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

# Seuils
MIN_JACCARD_WEIGHT = 0.1 
GRAPH_NAME = "protein_domain_graph"
RELATIONSHIP_TYPE = "SIMILAR"
IMPORT_BATCH_SIZE = 2500  

def import_proteins_and_domains(col, driver):
    """
    1) Crée les nœuds Protein et Domain
    2) Crée les relations HAS_DOMAIN
    à partir de la collection Mongo.
    """
    # On récupère toutes les protéines
    cursor = col.find({}, projection={
        "_id": 1,
        "uniprot_id": 1,
        "entry_name": 1,
        "organism": 1,
        "sequence.aa": 1,
        "sequence.length": 1,
        "ec_numbers": 1,
        "interpro_ids": 1,
        "is_labelled": 1,
    })

    with driver.session() as session:
        # Création des contraintes (Index uniques)
        print("🔒 Vérification des contraintes Neo4j...")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Protein) REQUIRE p.uniprot_id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Domain) REQUIRE d.interpro_id IS UNIQUE")
        # Index secondaire pour recherche rapide
        session.run("CREATE INDEX IF NOT EXISTS FOR (p:Protein) ON (p.organism)")

        batch = []
        total_processed = 0

        for doc in cursor:
            uniprot_id = doc.get("uniprot_id") or doc.get("_id")
            if not uniprot_id:
                continue

            entry_name = doc.get("entry_name")
            organism = doc.get("organism")
            length = doc.get("sequence", {}).get("length")
            ec_numbers = doc.get("ec_numbers", [])
            is_labelled = bool(doc.get("is_labelled", False))
            interpro_ids = doc.get("interpro_ids", [])

            batch.append({
                "uniprot_id": uniprot_id,
                "entry_name": entry_name,
                "organism": organism,
                "length": length,
                "ec_numbers": ec_numbers,
                "is_labelled": is_labelled,
                "interpro_ids": interpro_ids,
            })

            if len(batch) >= IMPORT_BATCH_SIZE:
                import_batch(session, batch)
                total_processed += len(batch)
                print(f"   Importé {total_processed} protéines...", end="\r")
                batch = []

        if batch:
            import_batch(session, batch)
            total_processed += len(batch)
        
        print(f"\n✅ Import terminé : {total_processed} protéines dans le graphe.")


def import_batch(session, proteins_batch):
    """
    Import d’un batch de protéines + leurs domaines dans Neo4j.
    """
    query = """
    UNWIND $rows AS row

    MERGE (p:Protein {uniprot_id: row.uniprot_id})
      SET p.entry_name = row.entry_name,
          p.organism   = row.organism,
          p.length     = row.length,
          p.ec_numbers = row.ec_numbers,
          p.is_labelled = row.is_labelled

    WITH p, row
    UNWIND row.interpro_ids AS interpro_id
      MERGE (d:Domain {interpro_id: interpro_id})
      MERGE (p)-[:HAS_DOMAIN]->(d)
    """
    session.run(query, rows=proteins_batch)


def build_similarity_edges_gds_math(driver):
    """
    Construit les arêtes SIMILAR entre protéines en utilisant
    l'algorithme de Similarité de Nœud (Node Similarity) de GDS,
    basé sur le coefficient de Jaccard sur les domaines partagés.
    Puis utilise une approche mathématique pour calculer 'shared_domains' et 'union_domains'.
    """
    print("\n--- DÉBUT DU TRAITEMENT SIMILARITÉ (GDS + MATH) ---")
    
    # 1. Nettoyage
    clean_previous_data(driver)
    
    # 2. Projection
    project_graph(driver)
    
    # 3. Calcul de similarité (Création des arêtes)
    run_gds_similarity(driver, threshold=MIN_JACCARD_WEIGHT)
    
    # 4. Nettoyage mémoire GDS 
    drop_graph_projection(driver)
    
    # 5. Préparation des données pour la formule mathématique
    precalculate_domain_counts(driver)
    
    # 6. Mise à jour des propriétés "shared_domains" et "union_domains" via la formule mathématique
    calculate_shared_union_domains_math(driver)
    
    print("--- TRAITEMENT TERMINÉ ---\n")

def clean_previous_data(driver):
    """Étape 1 : Nettoie les anciennes relations et la projection GDS si elle existe."""

    print("1) Nettoyage des anciennes relations et projections...")

    with driver.session() as session:
        # Suppression sécurisée des relations par lots
        session.run(f"""
        CALL apoc.periodic.iterate(
            'MATCH ()-[r:{RELATIONSHIP_TYPE}]-() RETURN r',
            'DELETE r',
            {{batchSize: 50000, parallel: true}}
        )
        """)
        # Suppression de la projection GDS si elle est restée en mémoire
        session.run(f"""
        CALL gds.graph.exists('{GRAPH_NAME}') YIELD exists
        WITH exists WHERE exists
        CALL gds.graph.drop('{GRAPH_NAME}') YIELD graphName
        RETURN graphName
        """)

def project_graph(driver):
    """Étape 2 : Projette le graphe en mémoire pour GDS."""

    print("2) Projection du graphe GDS...")

    query = f"""
    CALL gds.graph.project(
        '{GRAPH_NAME}',
        ['Protein', 'Domain'],
        'HAS_DOMAIN'
    )
    YIELD graphName, nodeCount, relationshipCount
    """
    with driver.session() as session:
        result = session.run(query)
        summary = result.single()
        if summary:
            print(f"  - Graphe projeté : {summary['nodeCount']} nœuds, {summary['relationshipCount']} relations.")
        else:
            raise Exception("Échec de la projection du graphe GDS.")
    
def run_gds_similarity(driver, threshold):
    """Étape 3 : Exécute l'algo Node Similarity (Jaccard) de GDS."""

    print(f"3) Calcul GDS (Jaccard > {threshold})...")

    query = f"""
    CALL gds.nodeSimilarity.write(
        '{GRAPH_NAME}',
        {{
            similarityMetric: 'JACCARD',
            writeRelationshipType: '{RELATIONSHIP_TYPE}',
            writeProperty: 'jaccard_weight',
            similarityCutoff: {threshold},
            concurrency: 4
        }}
    )
    YIELD nodesCompared, relationshipsWritten
    """
    with driver.session() as session:
        result = session.run(query)
        summary = result.single()
        print(f"  - GDS terminé : {summary['relationshipsWritten']} relations créées.")

def drop_graph_projection(driver):
    """Étape 4 : Libère la mémoire GDS en supprimant la projection."""

    print("4) Suppression de la projection GDS...")

    with driver.session() as session:
        session.run(f"CALL gds.graph.drop('{GRAPH_NAME}') YIELD graphName")
    
def precalculate_domain_counts(driver):
    """Étape 5 : Calcule le nombre de domaines par protéine (nécessaire pour la méthode mathématique du calcul des propriétés de SIMILAR)."""

    print("5) Pré-calcul du nombre de domaines par protéine...")

    query = """
    CALL apoc.periodic.iterate(
        "MATCH (p:Protein) RETURN p",
        "SET p.domain_count = COUNT { (p)-[:HAS_DOMAIN]->() }",
        {batchSize: 10000, parallel: true}
    )
    """
    with driver.session() as session:
        session.run(query)

def calculate_shared_union_domains_math(driver):
    print("6) 🚀 Calcul final des propriétés (Math formula)...")
    # Cette requête met à jour les propriétés shared_domains et union_domains
    # sans avoir à refaire des MATCH lourds sur les nœuds Domain.
    query = f"""
    CALL apoc.periodic.iterate(
        "MATCH (p1:Protein)-[r:{RELATIONSHIP_TYPE}]->(p2:Protein) RETURN p1, r, p2",
        "
            WITH p1.domain_count AS A, p2.domain_count AS B, r.jaccard_weight AS J, r
            
            // Math magic: Intersection = (J * (A + B)) / (1 + J)
            WITH A, B, r, toInteger(round((J * (A + B)) / (1.0 + J))) AS intersect
            
            SET r.shared_domains = intersect,
                r.union_domains = (A + B) - intersect
        ",
        {{batchSize: 5000, parallel: true, retries: 3}}
    )
    """
    with driver.session() as session:
        session.run(query)

# --- MAIN ---

if __name__ == "__main__":
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col = db[COLLECTION_NAME] # "all_proteins"

    # Connexion neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # Étape 1 : Création des nœuds
        import_proteins_and_domains(col, driver)
        
        # Étape 2 : Création des liens de similarité
        # Note : On utilise la version 'math' car elle est plus performante pour les gros volumes
        build_similarity_edges_gds_math(driver)
        
    finally:
        driver.close()
        client.close()
        print("🎉 Terminé.")