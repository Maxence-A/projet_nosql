async function runDetection() {
    const btn = document.getElementById('btnDetect');
    const loader = document.getElementById('loaderDetect');
    const resultsDiv = document.getElementById('resultsDetect');
    
    // UI Updates
    btn.disabled = true;
    loader.style.display = 'block';
    resultsDiv.style.display = 'none';

    try {
        const response = await fetch('/api/detect', { method: 'POST' });
        const result = await response.json();

        if (result.status === 'success') {
            const data = result.data;
            
            // 1. Remplir les statistiques
            document.getElementById('statTotalComm').innerText = data.total_communities;
            document.getElementById('statTotalProt').innerText = data.total_proteins_in_communities;
            document.getElementById('statAvgSize').innerText = Math.round(data.avg_community_size);
            document.getElementById('statLabelRate').innerText = (data.overall_labeling_rate * 100).toFixed(2) + '%';
            
            // 2. Remplir le Tableau TOP 5
            const tbody = document.getElementById('topCommunitiesTable');
            tbody.innerHTML = '';
            
            // On prend les 20   premières
            data.communities.slice(0, 20).forEach((comm, index) => {
                const percentage = (comm.labeling_rate * 100).toFixed(1);
                
                // Badges d'état
                let statusBadge;
                if (comm.unique_ec_numbers === 0) {
                    statusBadge = '<span class="badge bg-secondary">⚠️ Inconnu (0%)</span>';
                } else {
                    statusBadge = `<span class="badge bg-info text-dark">${comm.unique_ec_numbers} Types EC</span>`;
                }

                // Couleur du taux
                const percentClass = comm.labeling_rate > 0 ? "text-success fw-bold" : "text-muted";

                const row = `
                    <tr>
                        <td>${index + 1}</td>
                        <td><strong>${comm.community_id}</strong></td>
                        <td>${comm.size}</td>
                        <td class="${percentClass}">${percentage}%</td>
                        <td>${comm.unique_ec_numbers}</td>
                        <td>${statusBadge}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
            
            // Affichage
            resultsDiv.style.display = 'block';
            
            // Débloquer l'étape 2
            const cardPredict = document.getElementById('cardPredict');
            cardPredict.style.opacity = "1";
            cardPredict.style.pointerEvents = "auto";

        } else {
            alert("Erreur: " + result.message);
        }
    } catch (error) {
        console.error(error);
        alert("Erreur lors de la communication avec le serveur.");
    } finally {
        btn.disabled = false;
        loader.style.display = 'none';
    }
}

/**
 * ÉTAPE 2 : COMPARAISON (SIMULATION)
 */
async function runComparison() {
    const btn = document.getElementById('btnCompare');
    const loader = document.getElementById('loaderCompare');
    const resultsDiv = document.getElementById('resultsCompare');
    const tbody = document.getElementById('tableComparisonBody');

    btn.disabled = true;
    loader.style.display = 'block';
    resultsDiv.style.display = 'none';
    tbody.innerHTML = '';

    try {
        const response = await fetch('/api/compare', { method: 'POST' });
        const result = await response.json();

        if (result.status === 'success') {
            const data = result.data.data;

            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Aucune communauté mixte (avec label + sans label) trouvée pour la comparaison.</td></tr>';
            }

            data.forEach(item => {
                // Création des badges pour l'Union (Liste)
                let unionBadges = '';
                if (Array.isArray(item.result_union)) {
                    unionBadges = item.result_union.map(ec => 
                        `<span class="badge bg-warning me-1 mb-1">${ec}</span>`
                    ).join('');
                } else {
                    unionBadges = item.result_union;
                }

                // Badge unique pour Majorité
                const majorityBadge = `<span class="badge bg-success">${item.result_majority}</span>`;

                // Surligner si différence
                const diffIcon = item.is_different ? '<i class="bi bi-exclamation-triangle-fill text-warning ms-2" title="Résultats différents"></i>' : '';

                const row = `
                    <tr>
                        <td>
                            <strong>n°${item.community_id}</strong>
                            <div class="small text-muted">${item.size} membres</div>
                        </td>
                        <td>
                            <span class="badge bg-dark rounded-pill">${item.nb_unknown_targets}</span>
                            <small class="text-muted">cibles</small>
                        </td>
                        <td>
                            ${majorityBadge} ${diffIcon}
                        </td>
                        <td>
                            ${unionBadges}
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });

            resultsDiv.style.display = 'block';
            resultsDiv.scrollIntoView({ behavior: 'smooth' });

        } else {
            alert("Erreur: " + result.message);
        }
    } catch (error) {
        console.error(error);
        alert("Erreur lors de la comparaison.");
    } finally {
        btn.disabled = false;
        loader.style.display = 'none';
    }
}

/**
 * APPLICATION FINALE (ÉCRITURE EN BASE)
 */
async function applyMethod(method) {
    let url = '';

    if (method === 'union') {
        url = '/api/apply/union';
    } else {
        url = '/api/apply/majority';
    }


    // 1. Masquer les boutons, Afficher la barre de progression
    document.getElementById('actionButtons').style.display = 'none';
    const progressDiv = document.getElementById('executionProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    progressDiv.style.display = 'block';

    // 2. Animation "Fausse" progression (car on ne peut pas savoir le % réel d'une requête HTTP bloquante)
    // On fait monter la barre jusqu'à 90% doucement
    let width = 0;
    const interval = setInterval(() => {
        if (width >= 90) {
            clearInterval(interval); // On attend la réponse à 90%
        } else {
            width++; 
            progressBar.style.width = width + '%';
            progressBar.innerText = width + '%';
            
            // Changer le texte pour faire patienter
            if(width === 30) progressText.innerText = "Exécution des requêtes Cypher...";
            if(width === 60) progressText.innerText = "Traitement par lots (Batches)...";
            if(width === 85) progressText.innerText = "Finalisation de l'écriture...";
        }
    }, 10); // Vitesse de l'animation

    try {
        const response = await fetch(url, { method: 'POST' });
        const result = await response.json();

        // Arrêter l'animation et remplir à 100%
        clearInterval(interval);
        progressBar.style.width = '100%';
        progressBar.innerText = '100%';
        progressBar.classList.remove('progress-bar-animated');

        // Petite pause visuelle
        await new Promise(r => setTimeout(r, 500));
        progressDiv.style.display = 'none';

        if (result.status === 'success') {
            // 3. Afficher le résultat
            const successDiv = document.getElementById('executionSuccess');
            const reportList = document.getElementById('reportList');
            const details = result.details;

            // Construction du rapport HTML
            let reportHtml = '';
            
            if (method === 'union') {
                reportHtml += `<li><strong><i class="fa-solid fa-box"></i> Batches APOC :</strong> ${details.batches}</li>`;
                reportHtml += `<li><strong><i class="fa-solid fa-arrows-rotate"></i> Opérations commises :</strong> ${details.committed}</li>`;
                reportHtml += `<li><strong><i class="fa-solid fa-triangle-exclamation"></i> Erreurs :</strong> ${details.errors}</li>`;
            } else {
                reportHtml += `<li><strong><i class="fa-solid fa-square-check"></i> Méthode :</strong> Vote Majoritaire</li>`;
                reportHtml += `<li><strong><i class="fa-solid fa-arrows-rotate"></i> Protéines mises à jour :</strong> ${details.committed}</li>`;
            }

            reportList.innerHTML = reportHtml;
            successDiv.style.display = 'block';

        } else {
            // Afficher l'erreur dans l'HTML au lieu d'une alerte
            const successDiv = document.getElementById('executionSuccess');
            successDiv.style.display = 'block';
            successDiv.innerHTML = `
                <div class="alert alert-danger">
                    <h4><i class="fa-solid fa-xmark"></i> Erreur</h4>
                    <p>${result.message}</p>
                    <button class="btn btn-outline-danger btn-sm" onclick="location.reload()">Réessayer</button>
                </div>
            `;
        }
    } catch (error) {
        console.error(error);
        alert("Erreur serveur fatale.");
        location.reload();
    }
}