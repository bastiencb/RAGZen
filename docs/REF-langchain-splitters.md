# Reference : LangChain Text Splitters — Options completes

## 1. RecursiveCharacterTextSplitter

Le splitter le plus utilise, baseline recommandee.

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `separators` | list[str] | ["\n\n", "\n", " ", ""] | Separateurs a essayer dans l'ordre |
| `chunk_size` | int | 4000 | Taille max en caracteres |
| `chunk_overlap` | int | 200 | Overlap en caracteres |
| `length_function` | Callable | len | Fonction de mesure (peut etre tiktoken) |
| `keep_separator` | bool \| "start" \| "end" | False | Garder le separateur dans le chunk |
| `add_start_index` | bool | False | Ajouter l'index de debut en metadata |
| `strip_whitespace` | bool | True | Nettoyer les espaces |
| `is_separator_regex` | bool | True | Traiter separateurs comme regex |

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000, chunk_overlap=200,
    separators=["\n\n", "\n", ". ", "? ", "! ", " "],
    keep_separator=True, add_start_index=True,
)
chunks = splitter.split_text(text)
```

## 2. RecursiveCharacterTextSplitter.from_language()

Splitter specifique par langage de programmation.

### Langages supportes (25+)

| Language enum | Separateurs principaux |
|---------------|----------------------|
| `Language.PYTHON` | \nclass , \ndef , \n\tdef , \n\n, \n |
| `Language.JAVASCRIPT` | \nfunction , \nconst , \nlet , \nvar , \nclass , \nif , \nfor |
| `Language.TYPESCRIPT` | idem JS + \ninterface , \ntype , \nenum |
| `Language.JAVA` | \nclass , \npublic , \nprotected , \nprivate , \nstatic , \nif , \nfor |
| `Language.GO` | \nfunc , \nvar , \nconst , \ntype , \nif , \nfor |
| `Language.RUST` | \nfn , \nconst , \nlet , \nenum , \nstruct , \nimpl , \ntrait , \nif , \nfor |
| `Language.CPP` | \nclass , \nvoid , \nint , \nfloat , \nif , \nfor , \nwhile |
| `Language.C` | \nvoid , \nint , \nfloat , \nif , \nfor , \nwhile |
| `Language.CSHARP` | \nclass , \nvoid , \nint , \nfloat , \npublic , \nprivate |
| `Language.RUBY` | \ndef , \nclass , \nmodule , \nif , \nunless , \nwhile |
| `Language.PHP` | \nfunction , \nclass , \nif , \nforeach , \nwhile |
| `Language.KOTLIN` | \nfun , \nval , \nvar , \nclass , \nif , \nfor |
| `Language.SCALA` | \ndef , \nval , \nvar , \nclass , \nobject , \ntrait |
| `Language.SWIFT` | \nfunc , \nclass , \nstruct , \nenum , \nif , \nfor |
| `Language.LUA` | \nfunction , \nlocal , \nif , \nfor , \nwhile |
| `Language.PERL` | \nsub , \nmy , \nif , \nunless , \nwhile , \nfor |
| `Language.HASKELL` | \nmain , \nlet , \nwhere , \nmodule |
| `Language.COBOL` | \nIDENTIFICATION , \nENVIRONMENT , \nDATA , \nPROCEDURE |
| `Language.POWERSHELL` | \nfunction , \nif , \nforeach , \nwhile |
| `Language.SOLIDITY` | \ncontract , \nfunction , \nevent , \nmodifier |
| `Language.ELIXIR` | \ndef , \ndefp , \ndefmodule , \nif , \ncase |
| `Language.HTML` | <div, <p, <br, <li, <h1-h6, <span, <table, <tr |
| `Language.LATEX` | \chapter, \section, \subsection, \begin, \end |
| `Language.MARKDOWN` | \n#{1,6} , ```, \n\*{3,}, \n---  |
| `Language.PROTO` | \nmessage , \nservice , \nenum , \nrpc |
| `Language.RST` | section separators |

```python
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON, chunk_size=1500, chunk_overlap=200
)
```

## 3. CharacterTextSplitter

Split simple sur un seul separateur.

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `separator` | str | "\n\n" | Separateur unique |
| `chunk_size` | int | 4000 | Taille max |
| `chunk_overlap` | int | 200 | Overlap |
| `is_separator_regex` | bool | False | Regex |

## 4. SemanticChunker (langchain_experimental)

Split par similarite semantique entre phrases adjacentes.

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `embeddings` | Embeddings | **Requis** | Instance du modele d'embedding |
| `buffer_size` | int | 1 | Phrases voisines a considerer |
| `add_start_index` | bool | False | Index en metadata |
| `breakpoint_threshold_type` | str | "percentile" | Methode de seuil |
| `breakpoint_threshold_amount` | float \| None | None | Valeur du seuil |
| `number_of_chunks` | int \| None | None | Nombre cible de chunks (override threshold) |
| `sentence_split_regex` | str | `(?<=[.?!])\s+` | Regex de split en phrases |
| `min_chunk_size` | int \| None | None | Taille min d'un chunk |

### Types de seuil

| Type | Description | Valeur typique |
|------|-------------|---------------|
| `percentile` | Split quand difference > N-ieme percentile | 95 |
| `standard_deviation` | Split quand difference > N ecarts-types | 3.0 |
| `interquartile` | Basee sur Q1-Q3 (moins sensible) | 1.5 |
| `gradient` | Difference d'ordre 2 | 0.01-0.2 |

### Algorithme
1. Split texte en phrases
2. Groupe phrases par groupes de 3
3. Calcule embeddings de chaque groupe
4. Compare similarite entre groupes adjacents
5. Split aux points de faible similarite (breakpoints)

```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import OllamaEmbeddings

splitter = SemanticChunker(
    embeddings=OllamaEmbeddings(model="nomic-embed-text"),
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=95,
    buffer_size=1,
)
chunks = splitter.split_text(text)
```

## 5. MarkdownHeaderTextSplitter

Split par headers Markdown avec contexte hierarchique.

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `headers_to_split_on` | list[tuple[str,str]] | **Requis** | (marker, key) ex: ("#", "h1") |
| `return_each_line` | bool | False | Retourner chaque ligne separement |
| `strip_headers` | bool | True | Supprimer les headers du contenu |

Headers supportes : # (h1), ## (h2), ### (h3), #### (h4), ##### (h5), ###### (h6)

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4")],
    strip_headers=True,
)
docs = splitter.split_text(markdown_text)
# Chaque doc a .metadata = {"h1": "Titre1", "h2": "Sous-titre", ...}
```

## 6. HTMLHeaderTextSplitter

Split par balises HTML header.

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `headers_to_split_on` | list[tuple[str,str]] | **Requis** | (tag, key) ex: ("h1", "Header 1") |
| `return_each_element` | bool | False | Retourner chaque element HTML |

Requires: `lxml`

```python
from langchain_text_splitters import HTMLHeaderTextSplitter

splitter = HTMLHeaderTextSplitter(
    headers_to_split_on=[("h1", "Header 1"), ("h2", "Header 2"), ("h3", "Header 3")]
)
docs = splitter.split_text(html_text)
```

## 7. HTMLSemanticPreservingSplitter

Split HTML en preservant la structure semantique.

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `headers_to_split_on` | list[tuple[str,str]] | **Requis** | Headers a tracker |
| `max_chunk_size` | int | None | Taille max (re-split avec Recursive si depasse) |
| `preserve_links` | bool | False | Preserver les liens HTML |
| `preserve_images` | bool | False | Preserver les references images |
| `custom_handlers` | dict | {} | Handlers custom par tag HTML |

## 8. RecursiveJsonSplitter

Split JSON en respectant la structure.

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `max_chunk_size` | int | 2000 | Taille max en caracteres |
| `min_chunk_size` | int | ~1500 | Taille min |

```python
from langchain_text_splitters import RecursiveJsonSplitter

splitter = RecursiveJsonSplitter(max_chunk_size=2000)
chunks = splitter.split_json(json_data)
```

## 9. TokenTextSplitter

Split par tokens (tiktoken).

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `encoding_name` | str | "gpt2" | Encodage tiktoken |
| `model_name` | str \| None | None | Modele (override encoding) |
| `chunk_size` | int | - | Limite en tokens |

## 10. SpacyTextSplitter

Split par phrases via spaCy.

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `pipeline` | str | "en_core_web_sm" | Modele spaCy |
| `max_length` | int | 1000000 | Max chars acceptes |
| `chunk_size` | int | - | Taille de chunk |
| `chunk_overlap` | int | - | Overlap |

Alternative rapide : `pipeline="sentencizer"`

## 11. NLTKTextSplitter

Split par phrases via NLTK.

| Parametre | Type | Defaut |
|-----------|------|--------|
| `chunk_size` | int | - |
| `chunk_overlap` | int | - |

## 12. PythonCodeTextSplitter

Specialise Python. Separateurs : `\nclass `, `\ndef `, `\n\tdef `, `\n\n`, `\n`, ` `, ``

## 13. JSFrameworkTextSplitter

Specialise React/Vue/Svelte. Detecte les composants custom.

| Parametre | Type | Defaut |
|-----------|------|--------|
| `chunk_size` | int | 2000 |
| `chunk_overlap` | int | 0 |

## Classe de base : TextSplitter

Parametres herites par tous les splitters :

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `chunk_size` | int | 4000 | Taille max |
| `chunk_overlap` | int | 200 | Overlap |
| `length_function` | Callable | len | Mesure de longueur |
| `keep_separator` | bool | False | Garder separateur |
| `add_start_index` | bool | False | Index en metadata |
| `strip_whitespace` | bool | True | Nettoyer espaces |

## Methodes communes

- `split_text(text: str) -> list[str]`
- `split_documents(documents: list[Document]) -> list[Document]`
- `create_documents(texts: list[str], metadatas: list[dict] | None) -> list[Document]`
