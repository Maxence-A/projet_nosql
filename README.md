
# Lancement de l’environnement & Chargement des données

## 1. Lancement des services MongoDB et Neo4j (Docker)

Le projet utilise **Docker** pour exécuter les deux bases NoSQL nécessaires :

* **MongoDB** (stockage documentaire)
* **Neo4j** (base de graphes)

Les services sont définis dans `docker-compose.yml`.

### Démarrer l’environnement

À la racine du projet :

<pre class="overflow-visible!" data-start="603" data-end="635"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>docker compose up -d
</span></span></code></div></div></pre>

Les deux services démarrent en arrière-plan.

### Vérification

<pre class="overflow-visible!" data-start="704" data-end="725"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>docker ps
</span></span></code></div></div></pre>

Vous devez voir au moins deux conteneurs en état `Up` :

* `nosql_mongo`
* `nosql_neo4j`

### Accès aux services

| Service       | Adresse                   |
| ------------- | ------------------------- |
| MongoDB       | `localhost:27017`       |
| Neo4j Browser | [http://localhost:7474]()    |
| Neo4j Bolt    | `bolt://localhost:7687` |

Identifiants Neo4j par défaut :

<pre class="overflow-visible!" data-start="1038" data-end="1082"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>username :</span><span></span><span>neo4j</span><span>
</span><span>password :</span><span></span><span>password</span><span>
</span></span></code></div></div></pre>

---

## 2. Chargement des données dans MongoDB

Les fichiers UniProt (`.tsv`) doivent être placés dans le dossier :

<pre class="overflow-visible!" data-start="1204" data-end="1217"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>data</span><span>/
</span></span></code></div></div></pre>

Le script `load_mongo.py` permet d'importer automatiquement toutes les protéines dans MongoDB.

### Exécuter le chargement

Depuis l’environnement Python du projet :

<pre class="overflow-visible!" data-start="1389" data-end="1421"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>python load_mongo.py
</span></span></code></div></div></pre>

Le script :

* lit le fichier `.tsv.gz`
* extrait les champs pertinents (ID, noms, séquence, InterPro, EC number…)
* transforme chaque entrée en document JSON structuré
* insère les documents dans la base `protein_db` (collection `proteins_mouse`)
* crée les index nécessaires

### Vérifier l’import

Entrer dans le shell MongoDB :

<pre class="overflow-visible!" data-start="1759" data-end="1806"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>docker </span><span>exec</span><span> -it nosql_mongo mongosh
</span></span></code></div></div></pre>

Puis :

<pre class="overflow-visible!" data-start="1816" data-end="1920"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-js"><span><span>use protein_db
show collections
db.</span><span>proteins_mouse</span><span>.</span><span>countDocuments</span><span>()
db.</span><span>proteins_mouse</span><span>.</span><span>findOne</span><span>()</span></span></code></div></div></pre>
