"""
Script pour charger un fichier UniProt .tsv dans MongoDB.
"""

import math
import sys
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    from pymongo import MongoClient
    from pymongo.errors import BulkWriteError
except Exception as e :
    raise ImportError("Please install pandas and pymongo: pip install pandas pymongo") from e


MONGO_URI = "mongodb://mongo:27017"
DB_NAME = "protein_db"
COLLECTION_NAME = "all_proteins"
BATCH_SIZE = 5000

def split_semicolon_field(val):
    """
    Découpe un champ de type 'a;b;c' en liste ['a', 'b', 'c'].
    Gère les NaN / None / chaînes vides.
    """
    if val is None:
        return []
    # cas NaN (float)
    if isinstance(val, float) and math.isnan(val):
        return []
    # conversion en str puis split
    return [x.strip() for x in str(val).split(";") if x.strip()]

def get_mongo_collection(reset=False):
    """Connecte à Mongo et vide la collection seulement si demandé."""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col = db[COLLECTION_NAME]
    
    if reset:
        print(f"🧹 Nettoyage de la collection '{COLLECTION_NAME}'...")
        col.delete_many({})
        col.drop_indexes()
    
    return col

def process_and_insert_chunk(chunk, col, organism_default):
    """Transforme un chunk Pandas en liste de dicts et insère dans Mongo."""
    docs = []
    for _, row in chunk.iterrows():
        entry = row.get("Entry")
        if not isinstance(entry, str): 
            continue

        seq = str(row.get("Sequence", ""))
        
        # Priorité : Organisme du fichier > Argument de la fonction
        org_in_file = row.get("Organism")
        final_organism = org_in_file if isinstance(org_in_file, str) else organism_default
        ec_numbers = split_semicolon_field(row.get("EC number", ""))

        doc = {
            "_id": entry,  # Entry est la clé primaire
            "uniprot_id": entry,
            "entry_name": row.get("Entry Name"),
            "organism": final_organism,
            "protein_names": split_semicolon_field(row.get("Protein names")),
            "sequence": {
                "length": row.get("Length") if "Length" in row else len(seq),
                "aa": seq
            },
            "interpro_ids": split_semicolon_field(row.get("InterPro")),
            "ec_numbers": ec_numbers,
            "is_labelled": len(ec_numbers) > 0,
            "last_updated": datetime.now()
        }
        docs.append(doc)

    if docs:
        try:
            # ordered=False permet de continuer même si un ID existe déjà (doublon)
            col.insert_many(docs, ordered=False)
            return len(docs)
        except BulkWriteError as bwe:
            return bwe.details['nInserted']
        except Exception as e:
            print(f"⚠️ Erreur d'insertion : {e}")
            return 0
    return 0

def load_tsv_smart(file_path, organism_label, reset_collection=False):
    """
    Charge un fichier TSV par morceaux (chunks) pour économiser la RAM.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Fichier introuvable : {file_path}")
        return

    print(f"🚀 Démarrage pour : {organism_label} (Fichier: {path.name})")
    
    # 1. Gestion de la connexion et du reset éventuel
    col = get_mongo_collection(reset=reset_collection)

    # 2. Lecture par Chunks (Streaming)
    total_inserted = 0
    
    # Détection automatique des colonnes pour éviter les erreurs
    with pd.read_csv(path, sep="\t", chunksize=BATCH_SIZE, dtype=str) as reader:
        for i, chunk in enumerate(reader):
            inserted = process_and_insert_chunk(chunk, col, organism_label)
            total_inserted += inserted
            print(f"   Batch {i+1} : +{inserted} docs (Total: {total_inserted})", end="\r")

    print(f"\n✅ Terminé pour {organism_label}. {total_inserted} documents ajoutés.")

def create_indexes():
    """Crée les index une seule fois à la fin."""
    print("🏗️ Création des index (cela peut prendre un moment)...")
    client = MongoClient(MONGO_URI)
    col = client[DB_NAME][COLLECTION_NAME]

    col.create_index("uniprot_id", unique=True)
    col.create_index("organism")  # Très important pour filtrer Mouse vs Human
    col.create_index("ec_numbers")
    # Index de recherche textuelle
    col.create_index([
        ("protein_names", "text"), 
        ("entry_name", "text"),
    ])
    print("✨ Index optimisés créés !")

if __name__ == "__main__":
    
    # --- ÉTAPE 1 : Charger la Souris (ET nettoyer la base avant) ---
    load_tsv_smart(
        file_path="data/uniprotkb_AND_model_organism_10090_2025_11_14.tsv", 
        organism_label="Mouse", 
        reset_collection=True  
    )

    # --- ÉTAPE 2 : Charger l'Humain (SANS nettoyer la base) ---
    load_tsv_smart(
        file_path="data/uniprot-compressed_true_download_true_fields_accession_2Cid_2Cprotei-2022.11.14-07.52.02.48.tsv", 
        organism_label="Human", 
        reset_collection=False
    )

    # --- ÉTAPE 3 : Créer les index à la fin ---
    create_indexes()