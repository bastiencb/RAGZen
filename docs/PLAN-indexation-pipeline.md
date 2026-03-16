# Plan : Pipeline d'indexation debug + Front dedie + Parametres fins

## Contexte

Le pipeline d'indexation actuel dans `rag_server.py` est monolithique : extraction, chunking, embedding et stockage sont enchaines sans visibilite. Les parametres (taille chunk, overlap, modele d'embedding) sont hardcodes. L'utilisateur veut :
1. Un **pipeline d'indexation transparent** avec logs a chaque etape
2. Un **front dedie a l'indexation** separe du chat
3. Un **controle fin des parametres** de chaque librairie (Unstructured, LangChain)
4. Le tout aligne sur l'**etat de l'art 2026**

## Fichiers a modifier/creer

| Fichier | Action |
|---------|--------|
| `rag_server.py` | Modifier : refactor pipeline en step functions, SSE endpoint, chunk inspection, config |
| `indexation.html` | Creer : front dedie indexation avec config panel complet |
| `index.html` | Modifier (minimal) : ajouter lien vers `/indexation` |

---

## 1. Backend : Config complete (rag_server.py)

### 1.1 IndexationConfig — tous les parametres exposables

```python
@dataclass
class IndexationConfig:
    # ── Unstructured : Partition ──
    partition_strategy: str = "auto"        # "auto" | "fast" | "hi_res" | "ocr_only"
    partition_languages: list[str] = field(default_factory=lambda: ["fra", "eng"])
    include_page_breaks: bool = False
    extract_images: bool = False            # hi_res only

    # ── Unstructured : Chunking natif (pour documents structures) ──
    unstructured_chunking: str = "by_title" # "basic" | "by_title" | "none"
    us_max_characters: int = 2000           # hard max par chunk
    us_new_after_n_chars: int = 1500        # soft max (commence un nouveau chunk)
    us_overlap: int = 200                   # overlap en caracteres
    us_overlap_all: bool = False            # overlap entre tous les chunks (pas juste les splittes)
    us_combine_text_under_n_chars: int = 500  # combine petites sections (by_title)
    us_multipage_sections: bool = True      # autoriser sections multi-pages (by_title)
    us_include_orig_elements: bool = True   # garder elements originaux en metadata

    # ── LangChain : RecursiveCharacterTextSplitter ──
    lc_chunk_size: int = 2000               # taille max en caracteres
    lc_chunk_overlap: int = 200             # overlap en caracteres
    lc_separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", "? ", "! ", " "])
    lc_keep_separator: bool = True
    lc_strip_whitespace: bool = True
    lc_add_start_index: bool = True         # utile pour debug

    # ── LangChain : SemanticChunker (langchain_experimental) ──
    semantic_enabled: bool = False           # desactive par defaut (lent)
    semantic_threshold_type: str = "percentile"  # "percentile" | "standard_deviation" | "interquartile" | "gradient"
    semantic_threshold_amount: float = 95.0  # 95 pour percentile, 3.0 pour stdev, etc.
    semantic_buffer_size: int = 1            # phrases voisines a considerer
    semantic_min_chunk_size: int | None = None

    # ── LangChain : MarkdownHeaderTextSplitter ──
    md_headers: list[tuple[str,str]] = field(default_factory=lambda: [
        ("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4")
    ])
    md_strip_headers: bool = True

    # ── LangChain : HTMLHeaderTextSplitter ──
    html_headers: list[tuple[str,str]] = field(default_factory=lambda: [
        ("h1", "Header 1"), ("h2", "Header 2"), ("h3", "Header 3")
    ])

    # ── LangChain : Code splitter ──
    code_chunk_size: int = 1500
    code_chunk_overlap: int = 200
    # Language auto-detecte depuis l'extension, mais overridable

    # ── LangChain : JSON splitter ──
    json_max_chunk_size: int = 2000

    # ── Preprocessing ──
    clean_whitespace: bool = True
    normalize_unicode: bool = True           # NFKC
    clean_special_chars: bool = False

    # ── Embedding ──
    embedding_model: str = "nomic-embed-text"
    embedding_batch_size: int = 32

    # ── Filtrage ──
    max_file_size_mb: int = 100
```

### 1.2 Pipeline decompose en step functions

Chaque etape retourne un dict detaille avec timing et stats :

**`step_extract(filepath, category, config)`**
- Documents → `partition(strategy=config.partition_strategy, languages=config.partition_languages)`
- Texte/Code/Markdown/HTML/Data → `extract_text_file(filepath)`
- Retourne : `{method, strategy_used, element_count, char_count, element_types: {Title: 5, NarrativeText: 20, Table: 2}, duration}`

**`step_preprocess(content, config)`**
- Nettoyage whitespace (regex: espaces multiples, tabs, \n\n\n+)
- Normalisation unicode NFKC
- Suppression caracteres speciaux optionnelle
- Retourne : `{original_chars, cleaned_chars, changes: ["whitespace: -340 chars", "unicode: 2 normalisations"], duration}`

**`step_chunk(content, filepath, category, config)`**
Routing selon categorie + config :
- `document` + `unstructured_chunking != "none"` → Unstructured `chunk_by_title` ou `chunk_elements`
- `document` + `unstructured_chunking == "none"` → LangChain recursive
- `document` + `semantic_enabled` → LangChain SemanticChunker
- `markdown` → MarkdownHeaderTextSplitter → RecursiveCharacterTextSplitter
- `html` → HTMLHeaderTextSplitter → RecursiveCharacterTextSplitter
- `code_python` → PythonCodeTextSplitter
- `code_*` → RecursiveCharacterTextSplitter.from_language(Language.*)
- `data` (JSON) → RecursiveJsonSplitter
- `data` (CSV) → RecursiveCharacterTextSplitter (separateurs lignes)
- `text` → RecursiveCharacterTextSplitter ou SemanticChunker si active
- Retourne : `{splitter_used, chunk_count, avg_size, min_size, max_size, sizes: [420, 380, 510...], contexts_found: ["Titre1 > Titre2", ...], duration}`

**`step_embed(chunks, config)`**
- Ollama `/api/embed` par batch de `config.embedding_batch_size`
- Retourne : `{model, dimensions, batch_count, total_tokens_approx, duration}`

**`step_store(collection, chunks, vectors, filepath, file_hash, config)`**
- Metadata enrichie : `embedding_model`, `chunk_strategy`, `chunk_size`, `chunk_overlap`
- Retourne : `{ids_stored, duplicates_skipped, duration}`

### 1.3 SSE endpoint : `GET /index/stream`

```
GET /index/stream?folder=<path>&config=<json_base64_encoded>
```

Evenements SSE (format `data: {...}\n\n`) :

| type | contenu |
|------|---------|
| `config` | `{...toute la config utilisee...}` |
| `discovery` | `{files: [{name, size, ext, category}], total}` |
| `file_start` | `{index, file, size, category}` |
| `file_step` | `{index, file, step, result: {...stats detaillees...}}` |
| `file_done` | `{index, file, chunk_count, total_duration, error}` |
| `file_skip` | `{index, file, reason: "already indexed"|"too large"|"unsupported"}` |
| `complete` | `{total_files, files_processed, files_skipped, total_chunks, errors, total_duration}` |
| `error` | `{message}` |

Headers : `Cache-Control: no-cache`, `X-Accel-Buffering: no`
Etapes bloquantes wrappees dans `asyncio.to_thread()`.

### 1.4 Endpoints supplementaires

**`GET /chunks?source=<filename>`** — Inspection des chunks
```json
{
  "source": "rapport.pdf",
  "chunks": [
    {"id": "abc_0", "text": "...", "metadata": {"context": "...", "chunk_index": 0, "embedding_model": "...", "chunk_strategy": "..."}}
  ],
  "total": 12
}
```

**`GET /index/config`** — Config courante
**`POST /index/config`** — Mettre a jour (persiste dans `~/.rag_local/indexation_config.json`)

**`GET /indexation`** — Sert `indexation.html`

---

## 2. Frontend : indexation.html

### 2.1 Layout

```
┌────────────────────────────────────────────────────────────────┐
│ TopBar : RAGZen | Indexation Pipeline | [← Chat]  [Ollama ●]  │
├────────────────────────────────────────────────────────────────┤
│ [Dossier: _________________________] [▶ Lancer l'indexation]   │
│ Progress: ████████████░░░░ 8/12 fichiers (1m 23s)             │
├──────────────────────┬─────────────────────────────────────────┤
│                      │                                         │
│  ┌ EXTRACTION ─────┐ │  FILE LIST (scrollable)                 │
│  │ Strategy: [auto▼]│ │                                         │
│  │ Langues: [fr,en] │ │  ┌ rapport.pdf ──────────── 2.3 MB ──┐ │
│  │ Page breaks: [ ] │ │  │ ✅ Extract  Unstructured/auto      │ │
│  │ Images: [ ]      │ │  │            45 elem (5T,20N,2Tab)   │ │
│  └──────────────────┘ │  │            0.8s                     │ │
│                      │  │ ✅ Preprocess 12340→11980 chars     │ │
│  ┌ CHUNKING ───────┐ │  │              whitespace:-340,nfkc:2 │ │
│  │                  │ │  │              0.02s                  │ │
│  │ ┌ Documents ──┐  │ │  │ ✅ Chunk    by_title, 12 chunks    │ │
│  │ │ Method:     │  │ │  │            avg:850 min:320 max:1800│ │
│  │ │ [by_title▼] │  │ │  │            0.1s                    │ │
│  │ │ max_chars:  │  │ │  │ ✅ Embed   12 vecs, 768 dims      │ │
│  │ │ [2000]      │  │ │  │            batch:1, 1.2s           │ │
│  │ │ soft_max:   │  │ │  │ ✅ Store   12 stored, 0 dup       │ │
│  │ │ [1500]      │  │ │  │            0.05s                   │ │
│  │ │ overlap:    │  │ │  └────────── total: 2.17s ────────────┘ │
│  │ │ [200]       │  │ │                                         │
│  │ │ combine<:   │  │ │  ┌ code.py ──────────────── 45 KB ───┐ │
│  │ │ [500]       │  │ │  │ ✅ Extract  text/utf-8             │ │
│  │ │ multipage:  │  │ │  │ ⏳ Chunk   PythonCodeTextSplitter  │ │
│  │ │ [✓]         │  │ │  └────────────────────────────────────┘ │
│  │ └─────────────┘  │ │                                         │
│  │                  │ │                                         │
│  │ ┌ Texte/MD ───┐  │ │                                         │
│  │ │ chunk_size:  │  │ │                                         │
│  │ │ [2000]       │  │ │                                         │
│  │ │ overlap:     │  │ │                                         │
│  │ │ [200]        │  │ │                                         │
│  │ │ separateurs: │  │ │                                         │
│  │ │ [defaut ▼]   │  │ │                                         │
│  │ └─────────────┘  │ │                                         │
│  │                  │ │                                         │
│  │ ┌ Semantic ───┐  │ │                                         │
│  │ │ Activer: [ ] │  │ │                                         │
│  │ │ Seuil: [▼]   │  │ │                                         │
│  │ │ Valeur: [95]  │  │ │                                         │
│  │ │ Buffer: [1]   │  │ │                                         │
│  │ └─────────────┘  │ │                                         │
│  │                  │ │                                         │
│  │ ┌ Code ───────┐  │ │                                         │
│  │ │ chunk_size:  │  │ │                                         │
│  │ │ [1500]       │  │ │                                         │
│  │ │ overlap:     │  │ │                                         │
│  │ │ [200]        │  │ │                                         │
│  │ └─────────────┘  │ │                                         │
│  └──────────────────┘ │                                         │
│                      │                                         │
│  ┌ PREPROCESSING ──┐ │                                         │
│  │ Whitespace: [✓] │ │                                         │
│  │ Unicode:    [✓] │ │                                         │
│  │ Special:    [ ] │ │                                         │
│  └──────────────────┘ │                                         │
│                      │                                         │
│  ┌ EMBEDDING ──────┐ │                                         │
│  │ Model: [▼]      │ │                                         │
│  │ Batch: [32]     │ │                                         │
│  └──────────────────┘ │                                         │
├──────────────────────┴─────────────────────────────────────────┤
│ CHUNK INSPECTOR  (clic sur un fichier pour voir ses chunks)    │
│ rapport.pdf — 12 chunks — by_title — nomic-embed-text         │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐         │
│ │ #1/12         │ │ #2/12         │ │ #3/12         │  ...    │
│ │ [Chap1>Art3]  │ │ [Chap1>Art4]  │ │ [Chap2]      │         │
│ │               │ │               │ │               │         │
│ │ Le present    │ │ Les parties   │ │ En cas de     │         │
│ │ contrat...    │ │ conviennent...│ │ litige...     │         │
│ │               │ │               │ │               │         │
│ │ 850 chars     │ │ 920 chars     │ │ 780 chars     │         │
│ │ context: ...  │ │ context: ...  │ │ context: ...  │         │
│ └───────────────┘ └───────────────┘ └───────────────┘         │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 Panneau Config — detail des sections

**EXTRACTION (Unstructured)**
| Controle | Type | Options | Defaut |
|----------|------|---------|--------|
| Strategie partition | select | auto, fast, hi_res, ocr_only | auto |
| Langues OCR | multi-select chips | fra, eng, deu, spa, ita, por, nld, ... | fra, eng |
| Inclure page breaks | checkbox | — | off |
| Extraire images | checkbox | — | off |

**CHUNKING — Documents (Unstructured natif)**
| Controle | Type | Range | Defaut |
|----------|------|-------|--------|
| Methode | select | basic, by_title, none (→ LangChain) | by_title |
| Max caracteres (hard) | slider+input | 500-5000 | 2000 |
| Soft max (new_after_n_chars) | slider+input | 200-4000 | 1500 |
| Overlap | slider+input | 0-500 | 200 |
| Overlap all | checkbox | — | off |
| Combine sections < N chars | slider+input | 0-2000 | 500 |
| Sections multi-pages | checkbox | — | on |
| Garder elements originaux | checkbox | — | on |

**CHUNKING — Texte / Markdown / HTML (LangChain)**
| Controle | Type | Range | Defaut |
|----------|------|-------|--------|
| Chunk size | slider+input | 200-5000 | 2000 |
| Overlap | slider+input | 0-1000 | 200 |
| Separateurs | select | defaut, paragraphes, phrases, custom | defaut |
| Keep separator | checkbox | — | on |
| Strip whitespace | checkbox | — | on |
| Add start index | checkbox | — | on |

**CHUNKING — Semantic (LangChain Experimental)**
| Controle | Type | Options | Defaut |
|----------|------|---------|--------|
| Activer | checkbox | — | off |
| Type de seuil | select | percentile, standard_deviation, interquartile, gradient | percentile |
| Valeur seuil | slider+input | 0-100 (percentile) / 0-5 (stdev) | 95 |
| Buffer size | slider+input | 0-5 | 1 |
| Min chunk size | input | 0-2000 | (vide=auto) |

**CHUNKING — Code (LangChain)**
| Controle | Type | Range | Defaut |
|----------|------|-------|--------|
| Chunk size | slider+input | 500-5000 | 1500 |
| Overlap | slider+input | 0-500 | 200 |
| Langues : auto-detecte, liste affichee : Python, JS, TS, Java, Go, Rust, C++, Ruby, PHP, Kotlin, etc.

**PREPROCESSING**
| Controle | Type | Defaut |
|----------|------|--------|
| Nettoyage whitespace | checkbox | on |
| Normalisation unicode (NFKC) | checkbox | on |
| Suppression caracteres speciaux | checkbox | off |

**EMBEDDING**
| Controle | Type | Options | Defaut |
|----------|------|---------|--------|
| Modele | select (dynamique depuis Ollama) | nomic-embed-text, bge-m3, ... | nomic-embed-text |
| Batch size | slider+input | 1-64 | 32 |

### 2.3 Composants React

- **TopBar** : logo, titre "Indexation Pipeline", lien retour chat, indicateur Ollama
- **ControlBar** : input dossier, bouton indexer, barre progress globale + timer
- **ConfigPanel** : panneau gauche scrollable, sections collapsibles (Extraction, Chunking Documents, Chunking Texte, Semantic, Code, Preprocessing, Embedding)
- **FileList** : panneau droit scrollable, fichiers expandables, chaque etape avec stats temps reel
- **PipelineStep** : composant reutilisable (icone status animee, nom, stats, timing)
- **ChunkInspector** : panneau bas, grille horizontale scrollable de cartes chunk

### 2.4 SSE consumption

```javascript
const es = new EventSource(`/index/stream?folder=${enc(path)}&config=${btoa(JSON.stringify(config))}`);
es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    // dispatch selon data.type : config, discovery, file_start, file_step, file_done, file_skip, complete, error
};
```

### 2.5 Stack technique

Identique a index.html : React 18 CDN, Babel in-browser, dark theme, CSS variables partagees.

---

## 3. Routing intelligent par type de fichier

Le pipeline choisit automatiquement la meilleure combinaison selon le type :

| Categorie | Extraction | Chunking | Parametres utilises |
|-----------|-----------|---------|-------------------|
| `document` (PDF/DOCX/PPTX/XLSX) | Unstructured `partition(strategy=...)` | Unstructured `chunk_by_title` ou `basic` | partition_strategy, us_* |
| `markdown` | lecture texte | LangChain `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter` | md_headers, lc_chunk_size, lc_overlap |
| `html` | lecture texte | LangChain `HTMLHeaderTextSplitter` + `RecursiveCharacterTextSplitter` | html_headers, lc_chunk_size, lc_overlap |
| `code_python` | lecture texte | LangChain `PythonCodeTextSplitter` | code_chunk_size, code_overlap |
| `code_*` | lecture texte | LangChain `RecursiveCharacterTextSplitter.from_language(Language.*)` | code_chunk_size, code_overlap |
| `data` (JSON) | lecture texte | LangChain `RecursiveJsonSplitter` | json_max_chunk_size |
| `data` (CSV) | lecture texte | LangChain `RecursiveCharacterTextSplitter` (sep: `\n`) | lc_chunk_size, lc_overlap |
| `text` | lecture texte | LangChain `RecursiveCharacterTextSplitter` | lc_chunk_size, lc_overlap, lc_separators |

**Override semantic** : si `semantic_enabled=True`, les categories `document` (avec `unstructured_chunking=none`), `text`, `markdown` utilisent `SemanticChunker` a la place.

**Langages supportes par le code splitter** (25+) :
Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, C#, Ruby, PHP, Kotlin, Scala, Swift, Lua, Perl, Haskell, COBOL, PowerShell, Solidity, Elixir, Visual Basic 6, HTML, LaTeX, Markdown, Protocol Buffers, reStructuredText

---

## 4. Sequence d'implementation

1. **Backend config** : `IndexationConfig` dataclass, `GET/POST /index/config`, persistence JSON
2. **Backend step functions** : `step_extract`, `step_preprocess`, `step_chunk`, `step_embed`, `step_store` — chacune avec timing et stats detaillees
3. **Backend SSE** : `GET /index/stream`, `GET /chunks`, `GET /indexation`
4. **Frontend** : `indexation.html` — config panel, file list, pipeline viz, chunk inspector
5. **Lien** : bouton dans index.html sidebar vers `/indexation`

---

## 5. Verification

- Lancer le serveur, ouvrir `http://localhost:8765/indexation`
- Verifier que la config est chargee et modifiable
- Indexer un dossier contenant PDF, .py, .md, .txt, .json
- Verifier chaque etape en temps reel dans la file list
- Changer la strategie de chunking (by_title → recursive → semantic)
- Re-indexer et comparer les chunks dans l'inspector
- Tester le chat (`/`) — doit fonctionner normalement
- Verifier que les metadata incluent `embedding_model`, `chunk_strategy`
