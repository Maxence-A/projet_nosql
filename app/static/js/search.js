
let currentProteinId = null;

// quand on appuie sur "Entrée" dans le champ de recherche
document.addEventListener('DOMContentLoaded', () => {
    
    // Gestion de la recherche
    const input = document.getElementById('searchInput');
    if (input) {
        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }

    // Gestion du changement de placeholder selon le type de recherche
    const typeSelector = document.getElementById('searchType');
    if (typeSelector && input) {
        typeSelector.addEventListener('change', () => {
            const val = typeSelector.value;
            if(val === 'id') input.placeholder = "Ex: P12345, A0A...";
            else if(val === 'name') input.placeholder = "Ex: Cellular tumor antigen p53";
            else if(val === 'entry_name') input.placeholder = "Ex: P53_HUMAN";
            else input.placeholder = "Nom, ID (ex: kinase, A0A...)";
        });
    }

    // Gestion du sélecteur de profondeur
    const depthSelector = document.getElementById('depthSelector');
    if (depthSelector) {
        depthSelector.addEventListener('change', (e) => {
            const depth = e.target.value;
            if (currentProteinId) {
                reloadGraphOnly(currentProteinId, depth);
            }
        });
    }

    // Vérification de l'URL au chargement de la page
    // Si l'utilisateur arrive directement sur http://.../#P12345 ou rafraîchit la page
    const hash = window.location.hash;
    if (hash && hash.length > 1) {
        const idFromHash = hash.substring(1); // On enlève le '#'
        // On charge la vue, mais false = on ne push pas un nouvel état dans l'historique
        loadDetailView(idFromHash, false);
    }
});

// Gestion de l'historique pour le bouton "Retour"
window.addEventListener('popstate', (event) => {
    const hash = window.location.hash;

    if (hash && hash.length > 1) {
        // S'il y a un hash (ex: #P12345), on extrait l'ID et on recharge les données
        const id = hash.substring(1);
        // On charge les données sans toucher à l'historique (false)
        loadDetailView(id, false); 
    } else {
        // S'il n'y a pas de hash, on revient à la liste des résultats
        // On passe false pour ne pas déclencher un history.back() supplémentaire
        showResultsList(false);
    }
});

async function performSearch() {
    const input = document.getElementById('searchInput');
    const query = input.value;
    const typeSelector = document.getElementById('searchType');
    const searchType = typeSelector ? typeSelector.value : 'combined';
    if (!query) return;

    try {
        const response = await fetch(`/api/search?q=${query}&type=${searchType}`);
        let results = await response.json();
        console.log("Résultats de la recherche:", results);
        console.log("Result 0", results[0]);

        if (searchType === 'id' && results.length != 0) {
            results = results[0]
        }

        input.value = ''; 
        input.blur(); 

        if (results.length === 1) {
            loadDetailView(results[0].uniprot_id);
        } else {
            showResultsTable(results, query);
        }
    } catch (error) {
        console.error("Erreur recherche:", error);
    }
}

function showResultsTable(results, query) {
    document.getElementById('detailSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultCount').innerText = results.length;
    
    const tbody = document.getElementById('resultsTableBody');
    tbody.innerHTML = '';

    const displaySpan = document.getElementById('queryDisplay');
    displaySpan.innerText = query ? `"${query}"` : "";
    
    results.forEach(p => {
        let rawName = (p.protein_names && p.protein_names.length > 0) ? p.protein_names[0] : 'N/A';
        let cleanName = rawName.split('(')[0].trim();

        tbody.innerHTML += `
            <tr style="cursor:pointer" onclick="loadDetailView('${p.uniprot_id}')">
                <td><b>${p.uniprot_id}</b></td>
                <td>${p.entry_name || ''}</td>
                <td>${cleanName}</td>
            </tr>
        `;
    });
}

function showResultsList(updateHistory = true) {
    document.getElementById('detailSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    
    if (updateHistory) {
        history.back(); 
    }
}

async function loadDetailView(id, updateHistory = true) {
    currentProteinId = id;

    const depthSelector = document.getElementById('depthSelector');
    if(depthSelector) depthSelector.value = "1";

    // Si on vient d'un clic (updateHistory=true), on change l'URL.
    // Si on vient du bouton Précédent/Suivant (updateHistory=false), l'URL a DÉJÀ changé.
    if (updateHistory) {
        history.pushState({ view: 'details', id: id }, "", `#${id}`);
    }

    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('detailSection').style.display = 'block';

    try {
        const response = await fetch(`/api/protein/${id}?depth=1`);
        const data = await response.json();
        
        if(data.error) {
            // Si l'ID dans l'URL est invalide
            alert("Protéine non trouvée");
            return;
        }

        let p = data.info; // Récupère l'info

        // 1. Si c'est une liste, on prend le premier élément
        if (Array.isArray(p)) {
            p = p.length > 0 ? p[0] : null;
        }

        // 2. Vérification de sécurité si l'objet est vide
        if (!p) {
            console.error("Données info vides ou nulles");
            document.getElementById('proteinInfoParams').innerHTML = `<div class="text-danger">Info non trouvée pour ${id}</div>`;
            return;
        }

        const ecList = (p.ec_numbers && p.ec_numbers.length > 0) ? p.ec_numbers.join(', ') : 'Aucun';
        const interproList = (p.interpro_ids && p.interpro_ids.length > 0) ? p.interpro_ids.join(', ') : 'Aucun';
        const sequenceAA = (p.sequence && p.sequence.aa) ? p.sequence.aa : '';
        const sequenceLen = (p.sequence && p.sequence.length) ? p.sequence.length : '0';

        document.getElementById('proteinInfoParams').innerHTML = `
            <div class="info-group">
                <p><strong>ID UniProt:</strong> ${p.uniprot_id}</p>
                <p><strong>Nom Entry:</strong> ${p.entry_name}</p>
                <p><strong>Nom Complet:</strong> ${p.protein_names || 'N/A'}</p>
                <p><strong>Numéros EC:</strong> ${ecList}</p>
                <p><strong>InterPro IDs (domaines):</strong> ${interproList}</p>
                <p><strong>Longueur de Séquence:</strong> ${sequenceLen}</p>
            </div>
        `;

        updateNeighborsList(data.graph);
        initCytoscape(data.graph);

    } catch (error) {
        console.error("Erreur chargement détails:", error);
    }
}

async function reloadGraphOnly(id, depth) {
    // Petit indicateur visuel de chargement (optionnel mais recommandé)
    const container = document.getElementById('viz');
    container.style.opacity = '0.5'; 
    
    try {
        console.log(`Chargement du graphe pour ${id} avec profondeur ${depth}...`);
        
        // Appel API avec le paramètre depth
        const response = await fetch(`/api/protein/${id}?depth=${depth}`);
        const data = await response.json();

        // Mise à jour de la liste des voisins (car il y en a plus en profondeur 2)
        updateNeighborsList(data.graph);

        // Redessiner le graphe
        initCytoscape(data.graph);
        
    } catch (error) {
        console.error("Erreur rechargement graphe:", error);
    } finally {
        container.style.opacity = '1';
    }
}

function updateNeighborsList(graphData) {
    const neighborsList = document.getElementById('neighborsList');
    neighborsList.innerHTML = '';
        
    if(graphData && Array.isArray(graphData)) {
         // 1. On filtre pour ne garder que les voisins
         let neighbors = graphData.filter(el => 
            el.group === 'nodes' && 
            (el.data.type === 'neighbor_d1' || el.data.type === 'neighbor_d2')
         );

         // 2. On trie : Profondeur 1 d'abord, puis alphabétique
         neighbors.sort((a, b) => {
             if (a.data.type !== b.data.type) {
                 return a.data.type === 'neighbor_d1' ? -1 : 1;
             }
             return a.data.label.localeCompare(b.data.label);
         });

         // 3. Génération du HTML
         neighbors.forEach(el => {
             const isD1 = el.data.type === 'neighbor_d1';
             const id = el.data.id;
             const label = el.data.label;
             
             const badgeColor = isD1 ? '#66a5e0' : '#d981a1'; 
             const badgeText = isD1 ? 'P1' : 'P2';

             neighborsList.innerHTML += `
                <span onclick="loadDetailView('${id}')"
                    class="badge rounded-pill shadow-sm"
                    title="Voir les détails de ${id}"
                    style="background-color: ${badgeColor}; 
                            cursor: pointer; 
                            font-size: 0.9em; 
                            padding: 8px 12px; 
                            color: #fff;"> ${label}
                </span>
             `;
         });
    }
}

function initCytoscape(elementsData) {
    // Vérification que la div existe
    const container = document.getElementById('viz');
    if (!container) return;

    // Initialisation
    const cy = cytoscape({
        container: container, 

        elements: elementsData, // Les données JSON formatées par Python

        style: [ 
            // --- NOEUDS ---
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'color': '#fff',
                    'text-outline-width': 2,
                    'text-outline-color': '#555',
                    'font-size': '10px'
                }
            },
            {
                selector: 'node[type="center"]',
                style: {
                    'background-color': '#5e35b1', // Violet
                    'width': 60,
                    'height': 60,
                    'font-weight': 'bold',
                    'font-size': '14px',
                    'text-outline-color': '#5e35b1'
                }
            },
            {
                selector: 'node[type="neighbor_d1"]',
                style: {
                    'background-color': '#66a5e0', // Bleu
                    'width': 40,
                    'height': 40,
                    'text-outline-color': '#66a5e0'
                }
            },
            {
                selector: 'node[type="neighbor_d2"]',
                style: {
                    'background-color': '#d981a1', // Rose
                    'width': 30, 'height': 30, 
                    'text-outline-color': '#d981a1'
                }
            },
            {
                selector: 'node[type="domain"]',
                style: {
                    'background-color': '#69deb9', // Vert
                    'shape': 'triangle',
                    'width': 30,
                    'height': 30,
                    'text-outline-color': '#69deb9',
                    'color': '#000',
                }
            },
            // --- ARÊTES (LIENS) ---
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#ccc',
                    'curve-style': 'bezier', // Pour de jolies courbes
                    'target-arrow-shape': 'triangle', // Flèche au bout
                }
            },
            {
                selector: 'edge[type="SIMILAR"]',
                style: {
                    'label': 'data(weight)',
                    'color': '#555',
                    'font-size': '8px',
                    'font-weight': 'bold',
                    'text-background-color': '#fff',
                    'text-background-opacity': 0.8,
                    'text-background-padding': '2px',
                    'text-rotation': 'autorotate',
                    'line-color': '#999',
                    // Epaisseur basée sur le poids Jaccard (si dispo)
                    'width': 'mapData(weight, 0, 1, 1, 5)' 
                }
            },
            {
                selector: 'edge[type="HAS_DOMAIN"]',
                style: {
                    'line-color': '#95e5cc',
                    'line-style': 'dashed',
                    'target-arrow-color': '#95e5cc',
                    'target-arrow-shape': 'diamond'
                }
            },
        ],

        layout: {
            name: 'cose', // Layout "Force Directed" (physique)
            animate: true,
            padding: 30,
            componentSpacing: 40,
            nodeOverlap: 20,
            refresh: 20,
            fit: true,
            randomize: false 
        }
    });

    // Ajout d'interaction : Clic sur un voisin pour naviguer
    cy.on('tap', 'node', function(evt){
        const node = evt.target;
        const type = node.data('type');
        const id = node.data('id');

        if (type === 'neighbor_d1' || type === 'neighbor_d2') {
            loadDetailView(id);
        }
    });
}