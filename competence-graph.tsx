import React, { useState, useEffect } from 'react';
import { Graph } from 'react-d3-graph';

const CompetenceGraph = () => {
  // États pour stocker les données
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Chargement des fichiers JSON
  useEffect(() => {
    const loadGraphData = async () => {
      try {
        setLoading(true);
        
        // Charger les compétences et prérequis depuis les fichiers spécifiés
        const competencesResponse = await fetch('/src/json/competences_uniques.json');
        const prerequisResponse = await fetch('/src/json/prerequis_uniques.json');
        
        if (!competencesResponse.ok || !prerequisResponse.ok) {
          throw new Error('Erreur lors du chargement des fichiers JSON');
        }
        
        const competences = await competencesResponse.json();
        const prerequis = await prerequisResponse.json();
        
        // Construire le graphe à partir des données chargées
        buildGraph(competences, prerequis);
      } catch (err) {
        console.error('Erreur:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    loadGraphData();
  }, []);
  
  // Fonction pour construire le graphe à partir des données JSON
  const buildGraph = (competences, prerequis) => {
    const nodes = [];
    const links = [];
    const nodeMap = new Map(); // Pour éviter les doublons
    
    // Ajouter les compétences comme nœuds
    Object.keys(competences).forEach(comp => {
      if (!nodeMap.has(comp)) {
        nodes.push({
          id: comp,
          color: "#7cc5ec",
          size: 800,
          type: "competence",
          // Ajuster la taille en fonction du nombre d'exercices
          size: Math.max(600, competences[comp].uuid.length * 200)
        });
        nodeMap.set(comp, true);
      }
    });
    
    // Ajouter les prérequis comme nœuds
    Object.keys(prerequis).forEach(prereq => {
      if (!nodeMap.has(prereq)) {
        nodes.push({
          id: prereq,
          color: "#f7a35c",
          size: 800,
          type: "prerequis",
          // Ajuster la taille en fonction du nombre d'exercices
          size: Math.max(600, prerequis[prereq].uuid.length * 200)
        });
        nodeMap.set(prereq, true);
      }
    });
    
    // Inférer les relations basées sur les exercices communs
    const exerciceToCompetence = new Map();
    
    // Construire un index inversé: exercice -> compétences
    Object.entries(competences).forEach(([comp, data]) => {
      data.uuid.forEach(uuid => {
        if (!exerciceToCompetence.has(uuid)) {
          exerciceToCompetence.set(uuid, []);
        }
        exerciceToCompetence.get(uuid).push(comp);
      });
    });
    
    // Inférer les relations directes entre prérequis et compétences
    // basées sur les exercices communs
    Object.entries(prerequis).forEach(([prereq, data]) => {
      data.uuid.forEach(uuid => {
        if (exerciceToCompetence.has(uuid)) {
          exerciceToCompetence.get(uuid).forEach(comp => {
            links.push({ source: prereq, target: comp });
          });
        }
      });
    });
    
    // Inférer les relations entre compétences basées sur la complexité
    // (hypothèse: une compétence présente dans moins d'exercices pourrait 
    // dépendre d'une compétence plus commune)
    const compsByFrequency = Object.entries(competences)
      .map(([comp, data]) => ({ 
        comp, 
        freq: data.uuid.length 
      }))
      .sort((a, b) => b.freq - a.freq);
    
    // Les compétences les plus fréquentes sont probablement des prérequis
    // pour les moins fréquentes
    for (let i = 0; i < compsByFrequency.length - 1; i++) {
      const potentialPrereq = compsByFrequency[i].comp;
      
      // Pour chaque compétence potentiellement dépendante
      for (let j = i + 1; j < compsByFrequency.length; j++) {
        const potentialDependent = compsByFrequency[j].comp;
        
        // Vérifier s'ils partagent des exercices
        const hasCommonExercises = competences[potentialPrereq].uuid.some(
          uuid => competences[potentialDependent].uuid.includes(uuid)
        );
        
        if (hasCommonExercises) {
          links.push({ 
            source: potentialPrereq, 
            target: potentialDependent,
            color: "#cccccc" // Lien plus discret car inféré
          });
        }
      }
    }
    
    // Filtrer les liens en double
    const uniqueLinks = links.filter((link, index, self) => 
      index === self.findIndex(l => 
        l.source === link.source && l.target === link.target
      )
    );
    
    setGraphData({ nodes, links: uniqueLinks });
  };
  
  // Configuration du graphe
  const graphConfig = {
    nodeHighlightBehavior: true,
    directed: true,
    d3: {
      gravity: -250,
      linkLength: 200,
      alphaTarget: 0.1
    },
    node: {
      color: "lightgreen",
      fontSize: 12,
      fontWeight: "bold",
      highlightStrokeColor: "red",
      labelPosition: "center",
      renderLabel: true,
      labelProperty: "id",
      viewGenerator: (node) => {
        const size = node.size / 20;
        const radius = size / 2;
        if (node.type === "competence") {
          return (
            <svg width={size} height={size}>
              <rect
                x="0"
                y="0"
                width={size}
                height={size}
                rx={5}
                fill={node.color}
                stroke="#333333"
                strokeWidth="2"
              />
            </svg>
          );
        } else {
          return (
            <svg width={size} height={size}>
              <circle
                cx={radius}
                cy={radius}
                r={radius}
                fill={node.color}
                stroke="#333333"
                strokeWidth="2"
              />
            </svg>
          );
        }
      }
    },
    link: {
      highlightColor: "lightblue",
      strokeWidth: 2,
      color: "#555555",
      semanticStrokeWidth: true,
      type: "CURVE_SMOOTH"
    },
    height: 700,
    width: 900
  };
  
  // Légende et statistiques
  const GraphInfo = () => {
    const competenceCount = graphData.nodes.filter(n => n.type === "competence").length;
    const prerequisCount = graphData.nodes.filter(n => n.type === "prerequis").length;
    const relationCount = graphData.links.length;
    
    return (
      <div className="mt-4 p-4 bg-gray-100 rounded-lg">
        <h3 className="text-lg font-bold mb-2">Informations sur le graphe</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-1">
            <h4 className="font-semibold mb-2">Légende</h4>
            <div className="flex flex-col gap-2">
              <div className="flex items-center">
                <div className="w-5 h-5 bg-blue-400 mr-2"></div>
                <span>Compétence ({competenceCount})</span>
              </div>
              <div className="flex items-center">
                <div className="w-5 h-5 bg-orange-400 rounded-full mr-2"></div>
                <span>Prérequis ({prerequisCount})</span>
              </div>
            </div>
          </div>
          <div className="col-span-1">
            <h4 className="font-semibold mb-2">Statistiques</h4>
            <ul className="list-disc pl-5">
              <li>Total des nœuds: {graphData.nodes.length}</li>
              <li>Total des relations: {relationCount}</li>
              <li>Type de graphe: Dirigé</li>
            </ul>
          </div>
        </div>
      </div>
    );
  };
  
  // Composant pour les contrôles du graphe
  const GraphControls = ({ onRefresh }) => (
    <div className="flex justify-end mb-4">
      <button 
        className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg mr-2"
        onClick={onRefresh}
      >
        Actualiser le graphe
      </button>
    </div>
  );
  
  // Affichage conditionnel en fonction de l'état
  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl">Chargement du graphe de compétences...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded">
        <h3 className="font-bold">Erreur de chargement</h3>
        <p>{error}</p>
        <p className="mt-2 text-sm">
          Vérifiez que les fichiers JSON existent bien aux emplacements suivants:
          <ul className="list-disc pl-5 mt-1">
            <li>src/json/competences_uniques.json</li>
            <li>src/json/prerequis_uniques.json</li>
          </ul>
        </p>
      </div>
    );
  }
  
  return (
    <div className="flex flex-col">
      <div className="bg-white p-4 rounded-lg shadow-md mb-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Graphe des compétences et prérequis</h2>
          <GraphControls onRefresh={() => window.location.reload()} />
        </div>
        <div className="border rounded-lg" style={{ height: '700px' }}>
          {graphData.nodes.length > 0 && (
            <Graph
              id="competence-graph"
              data={graphData}
              config={graphConfig}
            />
          )}
        </div>
      </div>
      <GraphInfo />
    </div>
  );
};

export default CompetenceGraph;