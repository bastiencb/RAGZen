#!/usr/bin/env python3
"""
RAGZen v2 — Backend API (FastAPI)
=====================================

Extraction intelligente avec Unstructured + découpage adapté avec LangChain.

Améliorations vs v1 :
  - Unstructured détecte la structure des documents (titres, paragraphes, tableaux…)
  - LangChain découpe intelligemment selon le type de fichier :
      • PDF/DOCX → par sections logiques (titres + paragraphes)
      • Markdown  → par headers (##, ###…)
      • HTML      → par balises de titre (h1, h2, h3…)
      • Python    → par fonctions et classes
      • Code (JS, Java, Go…) → par blocs logiques
      • CSV/JSON  → par enregistrements
      • Texte brut → par paragraphes avec fallback récursif
  - Chaque chunk embarque son contexte hiérarchique (ex: "Chapitre 3 > Article 7")

Prérequis :
  pip install fastapi uvicorn chromadb requests \\
    unstructured[all-docs] \\
    langchain langchain-text-splitters \\
    --break-system-packages

  # Pour les PDF avec OCR (optionnel mais recommandé) :
  sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils libmagic1

  ollama pull bge-m3
  ollama pull mistral-nemo

Lancement :
  python rag_server_v2.py
  → http://localhost:8765
"""

import hashlib
import logging
import os
import re
import shutil
from pathlib import Path

import chromadb
import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rag-local")

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "bge-m3"
LLM_MODEL = "mistral-nemo"

CHROMA_PERSIST_DIR = os.path.expanduser("~/.rag_local/chroma_db")
COLLECTION_NAME = "mes_documents"

# Tailles de chunks par type (en caractères)
CHUNK_SIZES = {
    "document": 1000,   # PDF, DOCX — sections logiques
    "markdown": 1000,   # Markdown — par headers
    "html": 1000,       # HTML — par balises titre
    "code": 1500,       # Code — par fonctions/classes (plus grand)
    "data": 800,        # CSV, JSON — par enregistrements
    "text": 800,        # Texte brut — fallback
}
CHUNK_OVERLAP = 200
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 Mo max par fichier

# Extensions supportées, classées par catégorie
EXT_CATEGORIES = {
    # Documents structurés → Unstructured
    ".pdf": "document",
    ".docx": "document",
    ".doc": "document",
    ".odt": "document",
    ".pptx": "document",
    ".xlsx": "document",
    ".epub": "document",
    ".rst": "document",
    ".rtf": "document",
    # Markdown
    ".md": "markdown",
    # HTML
    ".html": "html",
    ".htm": "html",
    ".xml": "html",
    # Code
    ".py": "code_python",
    ".js": "code_js",
    ".ts": "code_js",
    ".jsx": "code_js",
    ".tsx": "code_js",
    ".java": "code_java",
    ".go": "code_go",
    ".rs": "code_rust",
    ".c": "code_c",
    ".cpp": "code_c",
    ".h": "code_c",
    ".rb": "code_ruby",
    ".php": "code_php",
    ".sql": "code_sql",
    ".sh": "code_bash",
    ".bash": "code_bash",
    ".yaml": "data",
    ".yml": "data",
    ".toml": "data",
    # Données
    ".csv": "data",
    ".json": "data",
    ".jsonl": "data",
    # Texte brut
    ".txt": "text",
    ".log": "text",
    ".ini": "text",
    ".cfg": "text",
    ".conf": "text",
    # ".env" volontairement exclu : risque d'indexer des secrets
}

SUPPORTED_EXTENSIONS = set(EXT_CATEGORIES.keys())

# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────

app = FastAPI(title="RAG Local API v2", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Extraction intelligente avec Unstructured
# ─────────────────────────────────────────────

def extract_with_unstructured(filepath: str) -> list[dict]:
    """
    Extrait les éléments structurés d'un document via Unstructured.
    Retourne une liste de dicts : {text, type, metadata}
    où type = Title, NarrativeText, Table, ListItem, etc.
    """
    from unstructured.partition.auto import partition

    elements = partition(
        filename=filepath,
        strategy="auto",          # "hi_res" pour OCR avancé sur PDF scannés
        languages=["fra", "eng"],  # Langues pour l'OCR
        include_page_breaks=False,
    )

    structured = []
    for el in elements:
        if not str(el).strip():
            continue
        structured.append({
            "text": str(el),
            "type": el.category if hasattr(el, "category") else "Text",
            "metadata": el.metadata.to_dict() if hasattr(el, "metadata") else {},
        })

    return structured


def extract_text_file(filepath: str) -> str:
    """Lit un fichier texte brut avec détection d'encodage."""
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Encodage non reconnu : {filepath}")


# ─────────────────────────────────────────────
# Découpage intelligent avec LangChain
# ─────────────────────────────────────────────

def chunk_structured_document(elements: list[dict], filepath: str) -> list[dict]:
    """
    Découpe un document structuré (issu d'Unstructured) en chunks intelligents.
    Regroupe les éléments par section (titre → contenu suivant).
    Chaque chunk contient le contexte hiérarchique.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    chunk_size = CHUNK_SIZES["document"]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "? ", "! ", " "],
    )

    chunks = []
    current_section_text = ""
    # Maintenir les titres de manière incrémentale (O(n) au lieu de O(n²))
    titles_seen = []
    current_context = ""

    for el in elements:
        if el["type"] == "Title":
            # Flush la section en cours
            if current_section_text.strip():
                full_text = f"[{current_context}]\n{current_section_text}" if current_context else current_section_text
                sub_chunks = splitter.split_text(full_text)
                for sc in sub_chunks:
                    chunks.append({
                        "text": sc,
                        "context": current_context,
                        "source": os.path.basename(filepath),
                    })

            # Nouveau titre → mettre à jour le contexte incrémentalement
            titles_seen.append(el["text"].strip())
            current_context = " > ".join(titles_seen[-3:])
            current_section_text = ""
        else:
            current_section_text += el["text"] + "\n\n"

    # Flush dernière section
    if current_section_text.strip():
        full_text = f"[{current_context}]\n{current_section_text}" if current_context else current_section_text
        sub_chunks = splitter.split_text(full_text)
        for sc in sub_chunks:
            chunks.append({
                "text": sc,
                "context": current_context,
                "source": os.path.basename(filepath),
            })

    return chunks


def chunk_markdown(text: str, filepath: str) -> list[dict]:
    """Découpe du Markdown en suivant la hiérarchie des headers."""
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

    # Étape 1 : découper par headers
    headers_to_split = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split)
    md_chunks = md_splitter.split_text(text)

    # Étape 2 : redécouper les sections trop longues
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZES["markdown"],
        chunk_overlap=CHUNK_OVERLAP,
    )

    chunks = []
    for doc in md_chunks:
        # Construire le contexte depuis les headers
        context_parts = []
        for key in ["h1", "h2", "h3", "h4"]:
            if key in doc.metadata:
                context_parts.append(doc.metadata[key])
        context = " > ".join(context_parts)

        # Préfixer avec le contexte
        full_text = f"[{context}]\n{doc.page_content}" if context else doc.page_content
        sub_chunks = char_splitter.split_text(full_text)

        for sc in sub_chunks:
            chunks.append({
                "text": sc,
                "context": context,
                "source": os.path.basename(filepath),
            })

    return chunks


def chunk_html(text: str, filepath: str) -> list[dict]:
    """Découpe du HTML en suivant les balises de titre."""
    from langchain_text_splitters import HTMLHeaderTextSplitter, RecursiveCharacterTextSplitter

    headers_to_split = [
        ("h1", "h1"),
        ("h2", "h2"),
        ("h3", "h3"),
    ]

    try:
        html_splitter = HTMLHeaderTextSplitter(headers_to_split_on=headers_to_split)
        html_chunks = html_splitter.split_text(text)
    except Exception:
        # Fallback si le HTML est mal formé
        return chunk_plain_text(text, filepath)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZES["html"],
        chunk_overlap=CHUNK_OVERLAP,
    )

    chunks = []
    for doc in html_chunks:
        context_parts = []
        for key in ["h1", "h2", "h3"]:
            if key in doc.metadata:
                context_parts.append(doc.metadata[key])
        context = " > ".join(context_parts)

        full_text = f"[{context}]\n{doc.page_content}" if context else doc.page_content
        sub_chunks = char_splitter.split_text(full_text)

        for sc in sub_chunks:
            chunks.append({
                "text": sc,
                "context": context,
                "source": os.path.basename(filepath),
            })

    return chunks


def chunk_python(text: str, filepath: str) -> list[dict]:
    """Découpe du Python par fonctions et classes."""
    from langchain_text_splitters import PythonCodeTextSplitter

    splitter = PythonCodeTextSplitter(
        chunk_size=CHUNK_SIZES["code"],
        chunk_overlap=CHUNK_OVERLAP,
    )
    raw_chunks = splitter.split_text(text)

    chunks = []
    for sc in raw_chunks:
        # Essayer de détecter le nom de la fonction/classe
        context = ""
        match = re.match(r"^(class|def)\s+(\w+)", sc.strip())
        if match:
            context = f"{match.group(1)} {match.group(2)}"

        chunks.append({
            "text": sc,
            "context": context,
            "source": os.path.basename(filepath),
        })

    return chunks


def chunk_code_generic(text: str, filepath: str, language: str) -> list[dict]:
    """Découpe du code générique (JS, Java, Go, etc.) par blocs logiques."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

    # Mapping catégorie → Language LangChain
    lang_map = {
        "code_js": Language.JS,
        "code_java": Language.JAVA,
        "code_go": Language.GO,
        "code_rust": Language.RUST,
        "code_c": Language.CPP,
        "code_ruby": Language.RUBY,
        "code_php": Language.PHP,
        "code_bash": Language.MARKDOWN,  # pas de bash natif, fallback
        "code_sql": Language.MARKDOWN,
    }

    lang = lang_map.get(language)

    if lang:
        try:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=lang,
                chunk_size=CHUNK_SIZES["code"],
                chunk_overlap=CHUNK_OVERLAP,
            )
            raw_chunks = splitter.split_text(text)
        except Exception:
            # Fallback
            return chunk_plain_text(text, filepath)
    else:
        return chunk_plain_text(text, filepath)

    chunks = []
    for sc in raw_chunks:
        chunks.append({
            "text": sc,
            "context": "",
            "source": os.path.basename(filepath),
        })

    return chunks


def chunk_data(text: str, filepath: str) -> list[dict]:
    """Découpe CSV/JSON/YAML par enregistrements ou blocs logiques."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    ext = Path(filepath).suffix.lower()

    if ext == ".csv":
        # Découper par lignes en gardant le header
        lines = text.split("\n")
        header = lines[0] if lines else ""
        chunks = []
        batch = []
        batch_len = 0

        for line in lines[1:]:
            if not line.strip():
                continue
            batch.append(line)
            batch_len += len(line)

            if batch_len >= CHUNK_SIZES["data"]:
                chunk_text = header + "\n" + "\n".join(batch)
                chunks.append({
                    "text": chunk_text,
                    "context": f"CSV ({len(batch)} lignes)",
                    "source": os.path.basename(filepath),
                })
                batch = []
                batch_len = 0

        if batch:
            chunk_text = header + "\n" + "\n".join(batch)
            chunks.append({
                "text": chunk_text,
                "context": f"CSV ({len(batch)} lignes)",
                "source": os.path.basename(filepath),
            })

        return chunks if chunks else [{"text": text, "context": "", "source": os.path.basename(filepath)}]

    elif ext in (".json", ".jsonl"):
        # Pour JSON lines : un chunk par groupe d'enregistrements
        # Pour JSON classique : découpage récursif
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZES["data"],
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n},\n", "\n}\n", "\n\n", "\n", " "],
        )
        raw_chunks = splitter.split_text(text)
        return [{"text": sc, "context": "JSON", "source": os.path.basename(filepath)} for sc in raw_chunks]

    else:
        # YAML, TOML, etc.
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZES["data"],
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " "],
        )
        raw_chunks = splitter.split_text(text)
        return [{"text": sc, "context": "", "source": os.path.basename(filepath)} for sc in raw_chunks]


def chunk_plain_text(text: str, filepath: str) -> list[dict]:
    """Découpage fallback pour du texte brut — par paragraphes."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZES["text"],
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "? ", "! ", " "],
    )
    raw_chunks = splitter.split_text(text)
    return [{"text": sc, "context": "", "source": os.path.basename(filepath)} for sc in raw_chunks]


# ─────────────────────────────────────────────
# Pipeline principal : extraction + chunking
# ─────────────────────────────────────────────

def process_file(filepath: str) -> list[dict]:
    """
    Pipeline complet pour un fichier :
    1. Détecte le type
    2. Extrait le contenu (Unstructured ou lecture directe)
    3. Découpe intelligemment selon le type

    Retourne une liste de dicts : {text, context, source}
    """
    ext = Path(filepath).suffix.lower()
    category = EXT_CATEGORIES.get(ext, "text")

    logger.info(f"  Traitement : {os.path.basename(filepath)} [{category}]")

    # ── Documents structurés → Unstructured + chunking par sections ──
    if category == "document":
        try:
            elements = extract_with_unstructured(filepath)
            if not elements:
                return []
            chunks = chunk_structured_document(elements, filepath)
            logger.info(f"    → Unstructured : {len(elements)} éléments → {len(chunks)} chunks")
            return chunks
        except Exception as e:
            logger.warning(f"    ⚠ Unstructured a échoué, fallback texte brut : {e}")
            # Fallback : essayer de lire comme du texte
            try:
                text = extract_text_file(filepath)
                return chunk_plain_text(text, filepath)
            except Exception:
                return []

    # ── Markdown → découpage par headers ──
    elif category == "markdown":
        text = extract_text_file(filepath)
        if not text.strip():
            return []
        return chunk_markdown(text, filepath)

    # ── HTML → découpage par balises titre ──
    elif category == "html":
        text = extract_text_file(filepath)
        if not text.strip():
            return []
        return chunk_html(text, filepath)

    # ── Python → découpage par fonctions/classes ──
    elif category == "code_python":
        text = extract_text_file(filepath)
        if not text.strip():
            return []
        return chunk_python(text, filepath)

    # ── Autres langages → découpage par blocs de code ──
    elif category.startswith("code_"):
        text = extract_text_file(filepath)
        if not text.strip():
            return []
        return chunk_code_generic(text, filepath, language=category)

    # ── Données (CSV, JSON, YAML…) → découpage par enregistrements ──
    elif category == "data":
        text = extract_text_file(filepath)
        if not text.strip():
            return []
        return chunk_data(text, filepath)

    # ── Texte brut → fallback récursif ──
    else:
        text = extract_text_file(filepath)
        if not text.strip():
            return []
        return chunk_plain_text(text, filepath)


# ─────────────────────────────────────────────
# Ollama
# ─────────────────────────────────────────────

def ollama_embed(texts: list[str]) -> list[list[float]]:
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["embeddings"]


def ollama_generate(prompt: str, system: str = "") -> str:
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1024},
    }
    if system:
        payload["system"] = system
    r = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["response"]


def check_ollama() -> dict:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        return {"online": True, "models": models}
    except Exception:
        return {"online": False, "models": []}


# ─────────────────────────────────────────────
# ChromaDB
# ─────────────────────────────────────────────

_chroma_client = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


def get_collection():
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def file_hash(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def get_indexed_sources() -> list[str]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    all_meta = collection.get(include=["metadatas"])
    return sorted(set(m["source"] for m in all_meta["metadatas"]))


# ─────────────────────────────────────────────
# Modèles Pydantic
# ─────────────────────────────────────────────

class IndexRequest(BaseModel):
    folder: str

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

    def validated_top_k(self) -> int:
        return max(1, min(self.top_k, 20))


# ─────────────────────────────────────────────
# Routes API
# ─────────────────────────────────────────────

@app.get("/")
def serve_ui():
    html_path = Path(__file__).parent / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(html_path, media_type="text/html")

@app.get("/status")
def api_status():
    ollama = check_ollama()
    collection = get_collection()
    return {
        "ollama": ollama["online"],
        "models": ollama["models"],
        "dbCount": collection.count(),
        "sources": get_indexed_sources(),
    }


@app.post("/index")
def api_index(req: IndexRequest):
    folder = os.path.abspath(req.folder)
    if not os.path.isdir(folder):
        raise HTTPException(400, f"Dossier introuvable : {folder}")

    ollama = check_ollama()
    if not ollama["online"]:
        raise HTTPException(503, "Ollama n'est pas accessible")
    if not any(EMBEDDING_MODEL in m for m in ollama["models"]):
        raise HTTPException(503, f"Modèle {EMBEDDING_MODEL} non installé dans Ollama")

    collection = get_collection()

    # Collecter les fichiers
    files = []
    for root, _, filenames in os.walk(folder):
        for fname in filenames:
            if Path(fname).suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(os.path.join(root, fname))

    if not files:
        raise HTTPException(400, f"Aucun document supporté dans {folder}")

    logger.info(f"📁 Indexation de {len(files)} fichier(s) depuis {folder}")

    total_new_chunks = 0
    files_processed = 0
    errors = []

    for filepath in files:
        filename = os.path.relpath(filepath, folder)
        fhash = file_hash(filepath)

        # Vérifier la taille du fichier
        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"  ⏭  {filename} (trop volumineux : {file_size / 1024 / 1024:.0f} Mo)")
            continue

        # Skip si déjà indexé (même hash)
        existing = collection.get(where={"file_hash": fhash})
        if existing and existing["ids"]:
            logger.info(f"  ⏭  {filename} (déjà indexé)")
            continue

        # Supprimer les anciens chunks du même fichier source (fichier modifié)
        old_chunks = collection.get(where={"source": filename})
        if old_chunks and old_chunks["ids"]:
            collection.delete(ids=old_chunks["ids"])
            logger.info(f"  🔄 {filename} : {len(old_chunks['ids'])} anciens chunks supprimés")

        try:
            # ── Pipeline v2 : extraction + chunking intelligent ──
            chunks = process_file(filepath)

            if not chunks:
                logger.warning(f"  ⚠  {filename} (vide ou non extractible)")
                continue

            # Générer les embeddings
            texts = [c["text"] for c in chunks]

            # Traiter par batch de 32 pour éviter les timeout
            all_embeddings = []
            batch_size = 32
            for b in range(0, len(texts), batch_size):
                batch = texts[b:b + batch_size]
                embs = ollama_embed(batch)
                all_embeddings.extend(embs)

            # Stocker dans ChromaDB
            ids = [f"{fhash}_{j}" for j in range(len(chunks))]
            metadatas = [
                {
                    "source": filename,
                    "file_hash": fhash,
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    "context": c.get("context", ""),
                    "category": EXT_CATEGORIES.get(Path(filepath).suffix.lower(), "text"),
                }
                for j, c in enumerate(chunks)
            ]

            collection.add(
                ids=ids,
                embeddings=all_embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            total_new_chunks += len(chunks)
            files_processed += 1
            logger.info(f"  ✅ {filename} → {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"  ❌ {filename} : {e}")
            errors.append({"file": filename, "error": str(e)})

    logger.info(f"🎉 Terminé : {total_new_chunks} nouveaux chunks, {files_processed} fichier(s)")
    return {
        "files_processed": files_processed,
        "new_chunks": total_new_chunks,
        "total": collection.count(),
        "errors": errors,
    }


@app.post("/search")
def api_search(req: QueryRequest):
    collection = get_collection()
    if collection.count() == 0:
        raise HTTPException(400, "Base vide — indexe d'abord des documents")

    query_embedding = ollama_embed([req.query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=req.validated_top_k(),
        include=["documents", "metadatas", "distances"],
    )

    formatted = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        meta = results["metadatas"][0][i]
        formatted.append({
            "text": results["documents"][0][i],
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "context": meta.get("context", ""),
            "category": meta.get("category", ""),
            "similarity": round(1 - distance, 4),
        })

    return {"results": formatted}


@app.post("/ask")
def api_ask(req: QueryRequest):
    collection = get_collection()
    if collection.count() == 0:
        raise HTTPException(400, "Base vide — indexe d'abord des documents")

    ollama = check_ollama()
    if not any(LLM_MODEL in m for m in ollama["models"]):
        raise HTTPException(503, f"Modèle {LLM_MODEL} non installé dans Ollama")

    # Recherche sémantique
    query_embedding = ollama_embed([req.query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=req.validated_top_k(),
        include=["documents", "metadatas", "distances"],
    )

    # Construire le contexte enrichi avec les infos de section
    context_parts = []
    sources = []
    seen_sources = set()

    for i in range(len(results["ids"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        source_name = meta["source"]
        context = meta.get("context", "")

        # Préfixer avec le contexte hiérarchique si disponible
        if context:
            context_parts.append(f"[{source_name} — {context}]\n{doc}")
        else:
            context_parts.append(f"[{source_name}]\n{doc}")

        if source_name not in seen_sources:
            sources.append({
                "name": source_name,
                "similarity": round(1 - distance, 4),
            })
            seen_sources.add(source_name)

    context_str = "\n\n---\n\n".join(context_parts)

    system_prompt = """Tu es un assistant qui répond aux questions en te basant UNIQUEMENT sur les extraits de documents fournis.
Règles :
- Réponds en français.
- Base ta réponse exclusivement sur les extraits fournis.
- Si les extraits ne contiennent pas assez d'information pour répondre, dis-le clairement.
- Cite les documents sources et les sections quand c'est pertinent.
- Sois précis et concis."""

    user_prompt = f"""Voici des extraits de documents pertinents :

{context_str}

---

Question : {req.query}

Réponse :"""

    answer = ollama_generate(user_prompt, system=system_prompt)

    return {
        "answer": answer,
        "sources": sources,
    }


@app.post("/reset")
def api_reset():
    global _chroma_client
    if os.path.exists(CHROMA_PERSIST_DIR):
        _chroma_client = None
        shutil.rmtree(CHROMA_PERSIST_DIR)
    return {"status": "ok", "message": "Base vectorielle supprimée"}


# ─────────────────────────────────────────────
# Lancement
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  RAG Local v2 — Backend API")
    print("  Unstructured + LangChain + ChromaDB + Ollama")
    print("  http://localhost:8765")
    print("=" * 55)

    ollama = check_ollama()
    if ollama["online"]:
        print(f"  ✅ Ollama connecté ({len(ollama['models'])} modèle(s))")
        for m in ollama["models"]:
            marker = "📌" if EMBEDDING_MODEL in m or LLM_MODEL in m else "  "
            print(f"     {marker} {m}")
    else:
        print("  ⚠️  Ollama non détecté — lance 'ollama serve'")

    collection = get_collection()
    print(f"  📦 ChromaDB : {collection.count()} chunks en base")
    print(f"  📂 Extensions supportées : {len(SUPPORTED_EXTENSIONS)}")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8765)
