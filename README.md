# 🔍 RAGZen

**Recherche sémantique + LLM sur tes propres documents, 100% local et gratuit.**

RAGZen te permet d'indexer n'importe quel type de document (PDF, DOCX, Markdown, code source, CSV, JSON…) dans une base vectorielle et de l'interroger en langage naturel, le tout sans envoyer tes données sur le cloud.

![Stack](https://img.shields.io/badge/Python-3.10+-blue)
![Ollama](https://img.shields.io/badge/Ollama-local_LLM-green)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector_store-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Fonctionnalités

- **Indexation intelligente** — Extraction structurée via [Unstructured](https://github.com/Unstructured-IO/unstructured) + découpage adapté par type de document via [LangChain](https://github.com/langchain-ai/langchain)
- **35+ formats supportés** — PDF, DOCX, PPTX, XLSX, Markdown, HTML, Python, JavaScript, Java, Go, Rust, CSV, JSON, YAML…
- **Recherche sémantique** — Retrouve les passages pertinents même sans correspondance de mots-clés
- **RAG complet** — Le LLM local génère une réponse en s'appuyant sur les documents retrouvés
- **Contexte hiérarchique** — Chaque chunk embarque son contexte (ex: "Chapitre 3 > Article 7 > Résiliation")
- **Interface web** — Frontend React avec chat, indexation, et visualisation des sources
- **CLI** — Script en ligne de commande pour l'indexation et les requêtes
- **100% local** — Aucune donnée ne quitte ta machine
- **Léger** — Un script Python + ChromaDB, pas de Docker obligatoire

## 🏗️ Architecture

```
Tes documents (PDF, DOCX, .py, .md, …)
        │
        ▼
┌─────────────────────┐
│   Unstructured       │  ← Extraction intelligente (titres, paragraphes, tableaux…)
└────────┬────────────┘
         ▼
┌─────────────────────┐
│   LangChain          │  ← Découpage adapté par type (sections, fonctions, headers…)
└────────┬────────────┘
         ▼
┌─────────────────────┐
│   Ollama (bge-m3)    │  ← Embedding (texte → vecteur)
└────────┬────────────┘
         ▼
┌─────────────────────┐
│   ChromaDB           │  ← Stockage vectoriel (persistant, local)
└────────┬────────────┘
         ▼
    Ta question
         │
         ▼
┌─────────────────────┐
│   Recherche cosinus  │  ← Top-K passages les plus proches
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Ollama (mistral-    │  ← Génération de la réponse
│   nemo:12b)          │
└─────────────────────┘
```

## 📋 Prérequis

- **Python 3.10+**
- **Ollama** — [ollama.com](https://ollama.com)
- ~8 Go de VRAM (GPU) pour le LLM, ou CPU (plus lent)

## 🚀 Installation

### 1. Cloner le repo

```bash
git clone https://github.com/<ton-user>/RAGZen.git
cd RAGZen
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

Pour l'OCR des PDF scannés (optionnel mais recommandé) :

```bash
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils libmagic1
```

### 3. Télécharger les modèles Ollama

```bash
ollama pull bge-m3           # Modèle d'embedding (multilingue)
ollama pull mistral-nemo     # LLM pour la génération de réponses
```

## 💻 Utilisation

### Option A — Interface web (recommandé)

```bash
# Lancer le backend
python rag_server.py
```

Le serveur démarre sur `http://localhost:8765`. Le frontend React (`rag_chat_ui.jsx`) s'y connecte.

L'interface propose :
- **Sidebar** : chemin du dossier à indexer, statut Ollama/ChromaDB, liste des documents indexés
- **Chat** : pose ta question, le système retrouve les passages pertinents et génère une réponse
- **Mode Recherche** : affiche les extraits bruts avec leur score de similarité (sans LLM)

### Option B — Ligne de commande

```bash
# Indexer un dossier
python rag_local.py index /chemin/vers/mes/documents

# Poser une question (RAG complet)
python rag_local.py ask "Quel est le délai de résiliation mentionné dans le contrat ?"

# Recherche sémantique seule (sans LLM)
python rag_local.py search "clause de résiliation"

# Voir l'état de la base
python rag_local.py status

# Réinitialiser la base
python rag_local.py reset
```

## 📁 Formats supportés

| Catégorie | Extensions | Méthode de découpage |
|---|---|---|
| Documents | `.pdf`, `.docx`, `.doc`, `.odt`, `.pptx`, `.xlsx`, `.epub`, `.rtf` | Unstructured → sections logiques |
| Markdown | `.md` | Par headers (`##`, `###`…) |
| HTML | `.html`, `.htm`, `.xml` | Par balises titre (`h1`, `h2`, `h3`) |
| Python | `.py` | Par fonctions et classes |
| JavaScript/TS | `.js`, `.ts`, `.jsx`, `.tsx` | Par blocs de code |
| Java | `.java` | Par blocs de code |
| Go | `.go` | Par blocs de code |
| Rust | `.rs` | Par blocs de code |
| C/C++ | `.c`, `.cpp`, `.h` | Par blocs de code |
| Données | `.csv`, `.json`, `.jsonl`, `.yaml`, `.toml` | Par enregistrements |
| Texte | `.txt`, `.log`, `.ini`, `.cfg`, `.conf` | Par paragraphes |

## ⚙️ Configuration

Les paramètres principaux se trouvent en haut de `rag_server.py` :

```python
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "bge-m3"          # Modèle d'embedding
LLM_MODEL = "mistral-nemo"          # Modèle génératif
CHROMA_PERSIST_DIR = "~/.rag_local/chroma_db"  # Stockage de la base
CHUNK_OVERLAP = 200                 # Chevauchement entre chunks
```

Les tailles de chunks sont adaptées par type :

```python
CHUNK_SIZES = {
    "document": 1000,   # PDF, DOCX
    "markdown": 1000,   # Markdown
    "html": 1000,       # HTML
    "code": 1500,       # Code source
    "data": 800,        # CSV, JSON
    "text": 800,        # Texte brut
}
```

## 🖥️ Configuration matérielle recommandée

| Config | Embedding | LLM | Performance |
|---|---|---|---|
| GPU 8 Go VRAM (ex: RTX 5070) | `bge-m3` | `mistral-nemo:12b` Q4 | ⭐⭐⭐ Optimal |
| GPU 6 Go VRAM | `bge-m3` | `mistral:7b` Q4 | ⭐⭐ Très bon |
| CPU seul, 12 Go RAM | `bge-m3` | `mistral:7b` Q4 | ⭐ Fonctionnel (lent) |
| CPU seul, 8 Go RAM | `all-MiniLM-L6-v2` | `phi3:mini` Q4 | Minimum viable |

## 📂 Structure du projet

```
RAGZen/
├── rag_server.py       # Backend API (FastAPI + Unstructured + LangChain)
├── rag_local.py        # CLI autonome (sans serveur web)
├── rag_chat_ui.jsx     # Frontend React (interface de chat)
├── requirements.txt    # Dépendances Python
├── .gitignore
├── LICENSE
└── README.md
```

## 🤝 Alternatives clé en main

Si tu cherches une solution packagée sans code :

- **[AnythingLLM](https://github.com/Mintplex-Labs/anything-llm)** — App desktop/Docker, très accessible
- **[Kotaemon](https://github.com/Cinnamon/kotaemon)** — Interface élégante, RAG hybride
- **[RAGFlow](https://github.com/infiniflow/ragflow)** — Puissant sur les documents complexes

L'avantage de RAGZen : légèreté, contrôle total du pipeline, et API REST intégrable dans n'importe quel projet.

## 📄 License

MIT
