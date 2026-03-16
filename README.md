# RAGZen

**Recherche semantique + LLM sur tes propres documents, 100% local et gratuit.**

RAGZen te permet d'indexer n'importe quel type de document (PDF, DOCX, Markdown, code source, CSV, JSON...) dans une base vectorielle et de l'interroger en langage naturel, le tout sans envoyer tes donnees sur le cloud.

![Stack](https://img.shields.io/badge/Python-3.10+-blue)
![Ollama](https://img.shields.io/badge/Ollama-local_LLM-green)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector_store-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Fonctionnalites

- **Indexation intelligente** -- Extraction structuree via [Unstructured](https://github.com/Unstructured-IO/unstructured) + decoupage adapte par type de document via [LangChain](https://github.com/langchain-ai/langchain)
- **35+ formats supportes** -- PDF, DOCX, PPTX, XLSX, Markdown, HTML, Python, JavaScript, Java, Go, Rust, CSV, JSON, YAML...
- **Recherche semantique** -- Retrouve les passages pertinents meme sans correspondance de mots-cles
- **RAG complet** -- Le LLM local genere une reponse en s'appuyant sur les documents retrouves
- **Contexte hierarchique** -- Chaque chunk embarque son contexte (ex: "Chapitre 3 > Article 7 > Resiliation")
- **Interface web integree** -- Frontend React servi directement par le backend, avec chat, indexation et visualisation des sources
- **CLI** -- Script en ligne de commande pour l'indexation et les requetes
- **API REST** -- Endpoints JSON pour integrer RAGZen dans n'importe quel projet
- **100% local** -- Aucune donnee ne quitte ta machine
- **Leger** -- Un script Python + ChromaDB, pas de Docker obligatoire

## Architecture

```
Tes documents (PDF, DOCX, .py, .md, ...)
        |
        v
+---------------------+
|   Unstructured       |  <- Extraction intelligente (titres, paragraphes, tableaux...)
+--------+------------+
         v
+---------------------+
|   LangChain          |  <- Decoupage adapte par type (sections, fonctions, headers...)
+--------+------------+
         v
+---------------------+
|   Ollama (bge-m3)    |  <- Embedding (texte -> vecteur)
+--------+------------+
         v
+---------------------+
|   ChromaDB           |  <- Stockage vectoriel (persistant, local)
+--------+------------+
         v
    Ta question
         |
         v
+---------------------+
|   Recherche cosinus  |  <- Top-K passages les plus proches
+--------+------------+
         v
+---------------------+
|  Ollama (mistral-    |  <- Generation de la reponse
|   nemo:12b)          |
+---------------------+
```

## Prerequis

- **Python 3.10+**
- **Ollama** -- [ollama.com](https://ollama.com)
- ~8 Go de VRAM (GPU) pour le LLM, ou CPU (plus lent)

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/bastiencb/RAGZen.git
cd RAGZen
```

### 2. Installer les dependances Python

```bash
pip install -r requirements.txt
```

Pour l'OCR des PDF scannes (optionnel, Linux uniquement) :

```bash
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils libmagic1
```

### 3. Telecharger les modeles Ollama

```bash
ollama pull bge-m3           # Modele d'embedding (multilingue)
ollama pull mistral-nemo     # LLM pour la generation de reponses
```

### Note Windows -- stockage des modeles sur un autre disque

Si ton disque C: manque d'espace, tu peux rediriger le stockage des modeles Ollama :

```powershell
setx OLLAMA_MODELS "E:\ollama\models"
```

Puis relancer Ollama pour que la variable soit prise en compte.

## Utilisation

### Option A -- Interface web (recommande)

```bash
python rag_server.py
```

Ouvre **http://localhost:8765** dans ton navigateur. L'interface web est servie directement par le backend, aucune installation frontend supplementaire n'est necessaire.

L'interface propose :
- **Sidebar** : chemin du dossier a indexer, statut Ollama/ChromaDB, liste des documents indexes
- **Chat** : pose ta question, le systeme retrouve les passages pertinents et genere une reponse
- **Mode Recherche** : affiche les extraits bruts avec leur score de similarite (sans LLM)
- **Parametres** : reglage du nombre de resultats (top_k)

### Option B -- Ligne de commande

```bash
# Indexer un dossier
python rag_local.py index /chemin/vers/mes/documents

# Poser une question (RAG complet)
python rag_local.py ask "Quel est le delai de resiliation mentionne dans le contrat ?"

# Recherche semantique seule (sans LLM)
python rag_local.py search "clause de resiliation"

# Voir l'etat de la base
python rag_local.py status

# Reinitialiser la base
python rag_local.py reset
```

### Option C -- API REST

Le serveur expose les endpoints suivants :

| Methode | Endpoint | Description | Body |
|---------|----------|-------------|------|
| `GET` | `/status` | Statut du systeme (Ollama, modeles, nb de chunks) | -- |
| `POST` | `/index` | Indexer un dossier | `{"folder": "/chemin/vers/docs"}` |
| `POST` | `/search` | Recherche semantique | `{"query": "...", "top_k": 5}` |
| `POST` | `/ask` | Question RAG (recherche + LLM) | `{"query": "...", "top_k": 5}` |
| `POST` | `/reset` | Reinitialiser la base vectorielle | -- |

Exemple avec curl :

```bash
# Verifier le statut
curl http://localhost:8765/status

# Indexer un dossier
curl -X POST http://localhost:8765/index \
  -H "Content-Type: application/json" \
  -d '{"folder": "/chemin/vers/documents"}'

# Poser une question
curl -X POST http://localhost:8765/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Quel est le delai de preavis ?", "top_k": 5}'
```

### Option D -- Tasks VSCode

Le projet inclut un fichier `.vscode/tasks.json` avec des taches preconfigures pour tester toutes les commandes directement depuis VSCode (`Ctrl+Shift+P` > "Tasks: Run Task") :

- **Demarrer Ollama** / **Demarrer le serveur** / **Demarrer tout**
- **Verifier le statut**
- **Indexer un dossier** (avec input du chemin)
- **Recherche semantique** (avec input de la question et top_k)
- **Poser une question RAG** (avec input de la question et top_k)
- **Reinitialiser la base**
- **Lister les modeles Ollama**

Chaque parametre est demande via un prompt interactif avec une valeur par defaut.

## Formats supportes

| Categorie | Extensions | Methode de decoupage |
|---|---|---|
| Documents | `.pdf`, `.docx`, `.doc`, `.odt`, `.pptx`, `.xlsx`, `.epub`, `.rtf` | Unstructured -> sections logiques |
| Markdown | `.md` | Par headers (`##`, `###`...) |
| HTML | `.html`, `.htm`, `.xml` | Par balises titre (`h1`, `h2`, `h3`) |
| Python | `.py` | Par fonctions et classes |
| JavaScript/TS | `.js`, `.ts`, `.jsx`, `.tsx` | Par blocs de code |
| Java | `.java` | Par blocs de code |
| Go | `.go` | Par blocs de code |
| Rust | `.rs` | Par blocs de code |
| C/C++ | `.c`, `.cpp`, `.h` | Par blocs de code |
| Donnees | `.csv`, `.json`, `.jsonl`, `.yaml`, `.toml` | Par enregistrements |
| Texte | `.txt`, `.log`, `.ini`, `.cfg`, `.conf` | Par paragraphes |

## Configuration

Les parametres principaux se trouvent en haut de `rag_server.py` :

```python
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "bge-m3"          # Modele d'embedding
LLM_MODEL = "mistral-nemo"          # Modele generatif
CHROMA_PERSIST_DIR = "~/.rag_local/chroma_db"  # Stockage de la base
CHUNK_OVERLAP = 200                 # Chevauchement entre chunks
```

Les tailles de chunks sont adaptees par type :

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

## Configuration materielle recommandee

| Config | Embedding | LLM | Performance |
|---|---|---|---|
| GPU 8 Go VRAM (ex: RTX 5070) | `bge-m3` | `mistral-nemo:12b` Q4 | Optimal |
| GPU 6 Go VRAM | `bge-m3` | `mistral:7b` Q4 | Tres bon |
| CPU seul, 12 Go RAM | `bge-m3` | `mistral:7b` Q4 | Fonctionnel (lent) |
| CPU seul, 8 Go RAM | `all-MiniLM-L6-v2` | `phi3:mini` Q4 | Minimum viable |

## Structure du projet

```
RAGZen/
├── rag_server.py        # Backend API (FastAPI + Unstructured + LangChain)
├── rag_local.py         # CLI autonome (sans serveur web)
├── rag_chat_ui.jsx      # Composant React source (reference)
├── index.html           # Interface web autonome (servie par le backend)
├── requirements.txt     # Dependances Python
├── .vscode/
│   └── tasks.json       # Taches VSCode pour tester les endpoints
├── .gitignore
├── LICENSE
└── README.md
```

## Alternatives cle en main

Si tu cherches une solution packagee sans code :

- **[AnythingLLM](https://github.com/Mintplex-Labs/anything-llm)** -- App desktop/Docker, tres accessible
- **[Kotaemon](https://github.com/Cinnamon/kotaemon)** -- Interface elegante, RAG hybride
- **[RAGFlow](https://github.com/infiniflow/ragflow)** -- Puissant sur les documents complexes

L'avantage de RAGZen : legerte, controle total du pipeline, et API REST integrable dans n'importe quel projet.

## License

MIT
