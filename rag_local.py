#!/usr/bin/env python3
"""
RAGZen — Recherche sémantique + LLM sur tes propres documents
================================================================

Stack :
  - Embedding   : bge-m3 (via Ollama)
  - Base vector. : ChromaDB (stockage local)
  - LLM         : mistral-nemo:12b (via Ollama)

Prérequis :
  pip install chromadb requests pymupdf python-docx --break-system-packages

  ollama pull bge-m3
  ollama pull mistral-nemo

Usage :
  # 1. Indexer un dossier de documents
  python rag_local.py index /chemin/vers/mes/documents

  # 2. Poser une question
  python rag_local.py ask "Quel est le délai de livraison mentionné dans le contrat ?"

  # 3. Recherche sémantique seule (sans LLM)
  python rag_local.py search "délai de livraison"

  # 4. Réinitialiser la base
  python rag_local.py reset
"""

import argparse
import os
import sys
import json
import hashlib
from pathlib import Path

import chromadb
import requests

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "bge-m3"
LLM_MODEL = "mistral-nemo"

# Dossier où ChromaDB stocke ses données (persistant entre les sessions)
CHROMA_PERSIST_DIR = os.path.expanduser("~/.rag_local/chroma_db")
COLLECTION_NAME = "mes_documents"

# Paramètres de chunking
CHUNK_SIZE = 800        # Nombre de caractères par chunk
CHUNK_OVERLAP = 200     # Chevauchement entre chunks

# Nombre de résultats retournés par la recherche
TOP_K = 5

# Extensions de fichiers supportées
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html", ".csv", ".json"}


# ─────────────────────────────────────────────
# Extraction de texte selon le type de fichier
# ─────────────────────────────────────────────

def extract_text_from_pdf(filepath: str) -> str:
    """Extrait le texte d'un PDF avec PyMuPDF (fitz)."""
    import fitz  # PyMuPDF
    doc = fitz.open(filepath)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def extract_text_from_docx(filepath: str) -> str:
    """Extrait le texte d'un fichier Word .docx."""
    from docx import Document
    doc = Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text_from_text(filepath: str) -> str:
    """Lit un fichier texte brut (txt, md, html, csv, json)."""
    encodings = ["utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Impossible de lire {filepath} avec les encodages testés")


def extract_text(filepath: str) -> str:
    """Dispatch vers le bon extracteur selon l'extension."""
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext == ".docx":
        return extract_text_from_docx(filepath)
    elif ext in {".txt", ".md", ".html", ".csv", ".json"}:
        return extract_text_from_text(filepath)
    else:
        raise ValueError(f"Extension non supportée : {ext}")


# ─────────────────────────────────────────────
# Découpage du texte en chunks
# ─────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Découpe le texte en morceaux avec chevauchement.
    On essaie de couper sur des fins de phrases/paragraphes.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Si on n'est pas à la fin, essayer de couper proprement
        if end < len(text):
            # Chercher le dernier saut de ligne ou point dans la zone
            for sep in ["\n\n", "\n", ". ", "? ", "! "]:
                last_sep = text[start:end].rfind(sep)
                if last_sep > chunk_size // 2:  # Pas trop au début
                    end = start + last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


# ─────────────────────────────────────────────
# Communication avec Ollama
# ─────────────────────────────────────────────

def ollama_embed(texts: list[str]) -> list[list[float]]:
    """Génère les embeddings via Ollama (bge-m3)."""
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["embeddings"]


def ollama_generate(prompt: str, system: str = "") -> str:
    """Génère une réponse via Ollama (mistral-nemo)."""
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,      # Peu créatif, on veut de la précision
            "num_predict": 1024,      # Longueur max de la réponse
        },
    }
    if system:
        payload["system"] = system

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["response"]


def check_ollama():
    """Vérifie qu'Ollama est accessible."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        return models
    except requests.ConnectionError:
        print("ERREUR : Ollama n'est pas lancé.")
        print("  → Lance Ollama avec : ollama serve")
        sys.exit(1)


# ─────────────────────────────────────────────
# Gestion de ChromaDB
# ─────────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    """Retourne la collection ChromaDB (la crée si nécessaire)."""
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # Distance cosinus
    )
    return collection


def file_hash(filepath: str) -> str:
    """Hash MD5 d'un fichier pour détecter les doublons."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


# ─────────────────────────────────────────────
# Commande : INDEX
# ─────────────────────────────────────────────

def cmd_index(folder: str):
    """Indexe tous les documents d'un dossier dans ChromaDB."""
    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        print(f"ERREUR : {folder} n'est pas un dossier valide.")
        sys.exit(1)

    # Vérifier Ollama et le modèle d'embedding
    models = check_ollama()
    if not any(EMBEDDING_MODEL in m for m in models):
        print(f"Le modèle {EMBEDDING_MODEL} n'est pas installé.")
        print(f"  → Installe-le avec : ollama pull {EMBEDDING_MODEL}")
        sys.exit(1)

    collection = get_collection()

    # Lister les fichiers supportés
    files = []
    for root, _, filenames in os.walk(folder):
        for fname in filenames:
            if Path(fname).suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(os.path.join(root, fname))

    if not files:
        print(f"Aucun document trouvé dans {folder}")
        print(f"  Extensions supportées : {', '.join(SUPPORTED_EXTENSIONS)}")
        return

    print(f"📁 {len(files)} document(s) trouvé(s) dans {folder}\n")

    total_chunks = 0
    for i, filepath in enumerate(files, 1):
        filename = os.path.relpath(filepath, folder)
        fhash = file_hash(filepath)

        # Vérifier si le fichier est déjà indexé (même hash)
        existing = collection.get(where={"file_hash": fhash})
        if existing and existing["ids"]:
            print(f"  [{i}/{len(files)}] ⏭  {filename} (déjà indexé)")
            continue

        try:
            # Extraction du texte
            text = extract_text(filepath)
            if not text.strip():
                print(f"  [{i}/{len(files)}] ⚠  {filename} (vide, ignoré)")
                continue

            # Découpage en chunks
            chunks = chunk_text(text)

            # Génération des embeddings par batch
            embeddings = ollama_embed(chunks)

            # Insertion dans ChromaDB
            ids = [f"{fhash}_{j}" for j in range(len(chunks))]
            metadatas = [
                {
                    "source": filename,
                    "file_hash": fhash,
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                }
                for j in range(len(chunks))
            ]

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
            )

            total_chunks += len(chunks)
            print(f"  [{i}/{len(files)}] ✅ {filename} → {len(chunks)} chunks")

        except Exception as e:
            print(f"  [{i}/{len(files)}] ❌ {filename} : {e}")

    print(f"\n🎉 Indexation terminée : {total_chunks} nouveaux chunks ajoutés")
    print(f"   Total en base : {collection.count()} chunks")


# ─────────────────────────────────────────────
# Commande : SEARCH (recherche sémantique seule)
# ─────────────────────────────────────────────

def cmd_search(query: str, top_k: int = TOP_K):
    """Recherche sémantique sans LLM — retourne les passages pertinents."""
    check_ollama()
    collection = get_collection()

    if collection.count() == 0:
        print("La base est vide. Indexe d'abord des documents avec : python rag_local.py index /dossier")
        return

    # Embedding de la requête
    query_embedding = ollama_embed([query])[0]

    # Recherche des chunks les plus proches
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    print(f"🔍 Résultats pour : \"{query}\"\n")
    print("=" * 60)

    for i in range(len(results["ids"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        similarity = 1 - distance  # cosine distance → similarity

        print(f"\n📄 [{i+1}] {meta['source']} (chunk {meta['chunk_index']+1}/{meta['total_chunks']})")
        print(f"   Similarité : {similarity:.2%}")
        print(f"   ---")
        # Afficher un extrait (premières lignes)
        preview = doc[:300] + "..." if len(doc) > 300 else doc
        print(f"   {preview}")
        print()

    return results


# ─────────────────────────────────────────────
# Commande : ASK (RAG complet)
# ─────────────────────────────────────────────

def cmd_ask(question: str, top_k: int = TOP_K):
    """RAG complet : recherche sémantique + génération de réponse par le LLM."""
    models = check_ollama()
    if not any(LLM_MODEL in m for m in models):
        print(f"Le modèle {LLM_MODEL} n'est pas installé.")
        print(f"  → Installe-le avec : ollama pull {LLM_MODEL}")
        sys.exit(1)

    collection = get_collection()

    if collection.count() == 0:
        print("La base est vide. Indexe d'abord des documents avec : python rag_local.py index /dossier")
        return

    print(f"🔍 Recherche dans {collection.count()} chunks...\n")

    # Recherche sémantique
    query_embedding = ollama_embed([question])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # Construire le contexte pour le LLM
    context_parts = []
    sources = set()
    for i in range(len(results["ids"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        sources.add(meta["source"])
        context_parts.append(f"[Extrait de {meta['source']}]\n{doc}")

    context = "\n\n---\n\n".join(context_parts)

    # Prompt système pour le RAG
    system_prompt = """Tu es un assistant qui répond aux questions en te basant UNIQUEMENT sur les extraits de documents fournis.
Règles :
- Réponds en français.
- Base ta réponse exclusivement sur les extraits fournis.
- Si les extraits ne contiennent pas assez d'information pour répondre, dis-le clairement.
- Cite les documents sources quand c'est pertinent.
- Sois précis et concis."""

    user_prompt = f"""Voici des extraits de documents pertinents :

{context}

---

Question : {question}

Réponse :"""

    print(f"📚 Sources consultées : {', '.join(sources)}")
    print(f"🤖 Génération de la réponse avec {LLM_MODEL}...\n")

    # Génération de la réponse
    response = ollama_generate(user_prompt, system=system_prompt)

    print("=" * 60)
    print(response)
    print("=" * 60)


# ─────────────────────────────────────────────
# Commande : RESET
# ─────────────────────────────────────────────

def cmd_reset():
    """Supprime toute la base vectorielle."""
    import shutil
    if os.path.exists(CHROMA_PERSIST_DIR):
        shutil.rmtree(CHROMA_PERSIST_DIR)
        print("🗑  Base vectorielle supprimée.")
    else:
        print("La base n'existe pas encore.")


# ─────────────────────────────────────────────
# Commande : STATUS
# ─────────────────────────────────────────────

def cmd_status():
    """Affiche l'état de la base et des modèles."""
    print("=== RAG Local — Status ===\n")

    # Vérifier Ollama
    try:
        models = check_ollama()
        print(f"✅ Ollama est actif ({len(models)} modèle(s) installé(s))")
        for m in models:
            marker = "📌" if EMBEDDING_MODEL in m or LLM_MODEL in m else "  "
            print(f"   {marker} {m}")
    except SystemExit:
        print("❌ Ollama n'est pas accessible")

    # Vérifier la base
    print()
    if os.path.exists(CHROMA_PERSIST_DIR):
        collection = get_collection()
        count = collection.count()
        print(f"✅ Base ChromaDB : {count} chunks indexés")
        print(f"   Emplacement : {CHROMA_PERSIST_DIR}")

        if count > 0:
            # Lister les fichiers indexés
            all_meta = collection.get(include=["metadatas"])
            sources = set(m["source"] for m in all_meta["metadatas"])
            print(f"   Documents : {len(sources)}")
            for s in sorted(sources):
                print(f"     📄 {s}")
    else:
        print("⚪ Base ChromaDB : non initialisée")


# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RAG Local — Recherche sémantique + LLM sur tes documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python rag_local.py index ./mes_documents
  python rag_local.py search "clause de résiliation"
  python rag_local.py ask "Quels sont les délais de paiement ?"
  python rag_local.py status
  python rag_local.py reset
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")

    # index
    p_index = subparsers.add_parser("index", help="Indexer un dossier de documents")
    p_index.add_argument("folder", help="Chemin vers le dossier contenant les documents")

    # search
    p_search = subparsers.add_parser("search", help="Recherche sémantique (sans LLM)")
    p_search.add_argument("query", help="Requête de recherche")
    p_search.add_argument("-k", type=int, default=TOP_K, help=f"Nombre de résultats (défaut: {TOP_K})")

    # ask
    p_ask = subparsers.add_parser("ask", help="Poser une question (RAG complet)")
    p_ask.add_argument("question", help="Question en langage naturel")
    p_ask.add_argument("-k", type=int, default=TOP_K, help=f"Nombre de contextes (défaut: {TOP_K})")

    # status
    subparsers.add_parser("status", help="État de la base et des modèles")

    # reset
    subparsers.add_parser("reset", help="Supprimer la base vectorielle")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args.folder)
    elif args.command == "search":
        cmd_search(args.query, args.k)
    elif args.command == "ask":
        cmd_ask(args.question, args.k)
    elif args.command == "status":
        cmd_status()
    elif args.command == "reset":
        cmd_reset()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
