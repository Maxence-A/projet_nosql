
// Configuration Neo4j
const NEO4J_URI = "bolt://localhost:7687";
const NEO4J_USER = "neo4j";
const NEO4J_PASS = "password"; 

// quand on appuie sur "Entrée" dans le champ de recherche
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('searchInput');
    if (input) {
        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
});

// Gestion de l'historique pour le bouton "Retour"
window.addEventListener('popstate', (event) => {
    // Si l'état est null (on est revenu à la racine), on réaffiche la liste
    if (!event.state) {
        showResultsList(false); // false = ne pas toucher à l'historique
    } else if (event.state.view === 'details') {
        // Si on fait "Suivant" pour revenir au détail
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('detailSection').style.display = 'block';
    }
});

async function performSearch() {
    const input = document.getElementById('searchInput');
    const query = input.value;
    if (!query) return;

    try {
        const response = await fetch(`/api/search?q=${query}&type=combined`);
        const results = await response.json();

        input.value = ''; 
        input.blur(); 

        if (results.length === 0) {
            alert("Aucun résultat !");
        } else if (results.length === 1) {
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
    if (query) {
        displaySpan.innerText = `"${query}"`;
    } else {
        displaySpan.innerText = "";
    }
    
    results.forEach(p => {
        // 1. Récupération du nom brut (premier de la liste ou chaîne vide)
        let rawName = 'N/A';
        if (p.protein_names && p.protein_names.length > 0) {
            rawName = p.protein_names[0];
        }

        // 2. Nettoyage : On coupe à partir de la première parenthèse '('
        // Ex: "UMP-CMP kinase (EC 2.7.4.14)..." devient "UMP-CMP kinase"
        let cleanName = rawName.split('(')[0].trim();

        // 3. Construction de la ligne (sans la colonne bouton)
        tbody.innerHTML += `
            <tr style="cursor:pointer" onclick="loadDetailView('${p.uniprot_id}')">
                <td><b>${p.uniprot_id}</b></td>
                <td>${p.entry_name || ''}</td>
                <td>${cleanName}</td>
            </tr>
        `;
    });
}

async function loadDetailView(id) {
    // Cela change l'URL en /#A0A... sans recharger la page
    history.pushState({ view: 'details', id: id }, "", `#${id}`);

    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('detailSection').style.display = 'block';

    try {
        const response = await fetch(`/api/protein/${id}`);
        const data = await response.json();
        const p = data.info;

        // Remplir Infos (Gauche)
        document.getElementById('proteinInfoParams').innerHTML = `
            <p><strong>ID:</strong> ${p.uniprot_id}</p>
            <p><strong>Nom:</strong> ${p.entry_name}</p>
            <p><strong>EC:</strong> ${p.ec_numbers ? p.ec_numbers.join(', ') : 'Aucun'}</p>
            <p><strong>Longueur:</strong> ${p.sequence ? p.sequence.length : 'N/A'}</p>
        `;

        // Remplir Voisins
        const neighborsList = document.getElementById('neighborsList');
        neighborsList.innerHTML = '';
        if(data.graph && data.graph.nodes) {
             data.graph.nodes.forEach(n => {
                 if(n.type === 'neighbor') {
                     neighborsList.innerHTML += `<li class="list-group-item small">${n.label}</li>`;
                 }
             });
        }

        drawNeovis(id);
    } catch (error) {
        console.error("Erreur chargement détails:", error);
    }
}

function showResultsList(updateHistory = true) {
    document.getElementById('detailSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    
    if (updateHistory) {
        history.back(); 
    }
}

function drawNeovis(id) {
    const config = {
        container_id: "viz",
        server_url: NEO4J_URI,
        server_user: NEO4J_USER,
        server_password: NEO4J_PASS,
        initial_cypher: `MATCH (center:Protein {uniprot_id: '${id}'}) OPTIONAL MATCH (center)-[r:SIMILAR]-(n:Protein) RETURN center, r, n LIMIT 50`,
        labels: { "Protein": { "caption": "entry_name", "size": "length" } },
        relationships: { "SIMILAR": { "thickness": "jaccard_weight", "caption": false } },
        initial_zoom: 0.7
    };
    new NeoVis.default(config).render();
}

function showResultsList() {
    document.getElementById('detailSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
}