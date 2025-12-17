async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error('Erreur réseau');
        const data = await response.json();

        // ---------------------------------------------------------
        // 1. Cartes KPI (Haut de page)
        // ---------------------------------------------------------
        document.getElementById('statsCards').innerHTML = `
            <div class="col-md-3 mb-3">
                <div class="card border-start border-4 border-primary p-3 shadow-sm">
                    <h3 class="mb-0">${data.mongo.total_proteins}</h3>
                    <small class="text-muted">Total Protéines</small>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card border-start border-4 border-warning p-3 shadow-sm">
                    <h3 class="mb-0">${data.neo4j.total_domains}</h3>
                    <small class="text-muted">Total Domaines</small>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card border-start border-4 border-success p-3 shadow-sm">
                    <h3 class="mb-0">${data.mongo.avg_sequence_length}</h3>
                    <small class="text-muted">Longueur de Séquence Moyenne</small>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card border-start border-4 border-danger p-3 shadow-sm">
                    <h3 class="mb-0">${data.neo4j.avg_degree}</h3>
                    <small class="text-muted">Degré Moyen (Connexions/Protéines)</small>
                </div>
            </div>
        `;

        // ---------------------------------------------------------
        // 2. Métriques Graphe détaillées
        // ---------------------------------------------------------
        document.getElementById('graphMetricsList').innerHTML = `
            <li class="list-group-item d-flex justify-content-between align-items-center bg-light">
                <strong>Vues d'ensemble</strong>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Total Protéines <span class="badge bg-primary rounded-pill">${data.mongo.total_proteins}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Total Domaines <span class="badge bg-info rounded-pill">${data.neo4j.total_domains}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Total Relations (Arêtes) <span class="badge bg-warning text-dark rounded-pill">${data.neo4j.total_similarities}</span>
            </li>
            
            <li class="list-group-item d-flex justify-content-between align-items-center bg-light mt-2">
                <strong>Détails Topologie</strong>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Degré Max <span class="badge bg-secondary rounded-pill">${data.neo4j.max_degree}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Écart-type Degré <span class="badge bg-secondary rounded-pill">${data.neo4j.std_degree}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Moy. Protéines/Domaine <span class="badge bg-secondary rounded-pill">${data.neo4j.avg_proteins_per_domain}</span>
            </li>
        `;

        // ---------------------------------------------------------
        // 3. Fonctions utilitaires
        // ---------------------------------------------------------
        const commonOptions = { responsive: true, maintainAspectRatio: false };
        const extractData = (list) => ({
            labels: list.map(item => item[0]), 
            data: list.map(item => item[1])    
        });

        // ---------------------------------------------------------
        // 4. Graphiques
        // ---------------------------------------------------------

        // Chart: Labelisés (Doughnut)
        new Chart(document.getElementById('labelChart'), {
            type: 'doughnut',
            data: {
                labels: [
                    'Labellisées (Origine)', 
                    'Labels Prédits (Calculés)', 
                    'Non-labellisées (Inconnues)'
                ],
                datasets: [{
                    data: [
                        data.mongo.labeled_proteins,           
                        data.neo4j.predicted_proteins,          
                        data.mongo.unlabeled_proteins  
                    ],
                    backgroundColor: [
                        '#4bc0c0', 
                        '#8ae2e2ff', 
                        '#e7e9ed'  
                    ],
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                let value = context.raw;
                                let total = context.chart._metasets[context.datasetIndex].total;
                                let percentage = Math.round((value / total) * 100) + '%';
                                return value + ' (' + percentage + ')';
                            }
                        }
                    }
                }
            }
        });

        const orgData = extractData(data.mongo.organism_stats || []);
        new Chart(document.getElementById('organismChart'), {
            type: 'pie',
            data: {
                labels: orgData.labels,
                datasets: [{
                    data: orgData.data,
                    backgroundColor: [
                        "#ff9f40",
                        "#9966ff",
                        "#4BC0C0",
                        '#FFCE56', 
                        '#FF6384',
                        '#36A2EB'
                    ],
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) label += ': ';
                                let value = context.raw;
                                let total = context.chart._metasets[context.datasetIndex].total;
                                // Calcul du pourcentage
                                let percentage = Math.round((value / total) * 100) + '%';
                                return label + value + ' (' + percentage + ')';
                            }
                        }
                    }
                }
            }
        });

        // Chart: Domaines (Pie)
        new Chart(document.getElementById('domainChart'), {
            type: 'doughnut',
            data: {
                labels: ['Protéines avec domaines', 'Protéines sans domaines'],
                datasets: [{
                    data: [data.mongo.proteins_with_domains, data.mongo.proteins_without_domains],
                    backgroundColor: ['#36a2eb', '#ff6384']
                }]
            },
            options: commonOptions
        });

        // Chart: Protéines Isolées vs Connectées 
        const isolated = data.neo4j.isolated_proteins;
        const connected = data.mongo.total_proteins - isolated;
        
        new Chart(document.getElementById('isolationChart'), {
            type: 'doughnut',
            data: {
                labels: ['Protéines connectées', 'Protéines isolées'],
                datasets: [{
                    data: [connected, isolated],
                    backgroundColor: ['#ffcd56', '#c9cbcf']
                }]
            },
            options: commonOptions
        });

        // Chart: Top 10 EC Numbers (Barre Horizontale)
        const ecData = extractData(data.mongo.top_ec_numbers);
        new Chart(document.getElementById('ecChart'), {
            type: 'bar',
            data: {
                labels: ecData.labels,
                datasets: [{
                    label: 'Occurrences',
                    data: ecData.data,
                    backgroundColor: '#ff9f40'
                }]
            },
            options: { ...commonOptions, indexAxis: 'y' }
        });

        // Chart: Top 10 InterPro (Barre Horizontale)
        const ipData = extractData(data.mongo.top_interpro_ids);
        new Chart(document.getElementById('interproChart'), {
            type: 'bar',
            data: {
                labels: ipData.labels,
                datasets: [{
                    label: 'Occurrences',
                    data: ipData.data,
                    backgroundColor: '#9966ff'
                }]
            },
            options: { ...commonOptions, indexAxis: 'y' }
        });


    } catch (error) {
        console.error("Erreur stats:", error);
        document.getElementById('statsCards').innerHTML = 
            `<div class="alert alert-danger w-100">Erreur: ${error.message}</div>`;
    }
}

document.addEventListener('DOMContentLoaded', loadStats);