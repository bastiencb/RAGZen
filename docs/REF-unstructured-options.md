# Reference : Unstructured — Options completes

## Partition Strategies (PDF/Images)

| Strategy | Description | Vitesse | Tables | Multi-colonne | Dependances |
|----------|-------------|---------|--------|---------------|-------------|
| `auto` | Choisit selon le doc | Variable | Conditionnel | Variable | Variable |
| `fast` | pdfminer text extraction | Tres rapide | Non | Mauvais | pdfminer |
| `hi_res` | detectron2_onnx layout analysis | Lent | Oui | Mauvais | detectron2_onnx |
| `ocr_only` | Tesseract OCR | Moyen | Non | Excellent | Tesseract |

## Partition Functions (23)

| Fonction | Formats | Parametres specifiques |
|----------|---------|----------------------|
| `partition()` | Auto-detect tous formats | `strategy`, `languages` |
| `partition_pdf()` | PDF | `strategy`, `languages`, `extract_images_in_pdf`, `extract_image_block_types`, `max_partition` |
| `partition_image()` | PNG, JPG, HEIC | `strategy`, `languages` |
| `partition_docx()` | DOCX | headers/footers auto |
| `partition_doc()` | DOC | Requires libreoffice |
| `partition_pptx()` | PPTX | slides |
| `partition_ppt()` | PPT | Requires libreoffice |
| `partition_xlsx()` | XLSX | Chaque sheet = Table element, `text_as_html` |
| `partition_csv()` / `partition_tsv()` | CSV/TSV | Single Table element, `text_as_html` |
| `partition_html()` | HTML | `url`, `headers`, `ssl_verify` |
| `partition_email()` | EML | `content_source`, `include_headers`, `process_attachments` |
| `partition_msg()` | MSG (Outlook) | `content_source`, `process_attachments` |
| `partition_text()` | TXT | `paragraph_grouper`, `max_partition` |
| `partition_md()` | Markdown | Requires pandoc |
| `partition_rst()` | reStructuredText | Requires pandoc |
| `partition_rtf()` | RTF | - |
| `partition_xml()` | XML | `xml_keep_tags`, `xml_path` |
| `partition_epub()` | EPUB | Requires pandoc |
| `partition_odt()` | ODT | Requires pandoc |
| `partition_org()` | Org-mode | Requires pandoc |

## Parametres globaux de partition

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `filename` | str | - | Chemin du fichier |
| `file` | file-like | None | Objet fichier |
| `text` | str | None | Texte brut |
| `strategy` | str | "auto" | Strategie : auto, fast, hi_res, ocr_only |
| `languages` | list[str] | - | Langues OCR : ["fra", "eng", "deu", ...] |
| `include_page_breaks` | bool | False | Inclure PageBreak elements |
| `max_partition` | int | 1500 | Max chars par element (ocr_only, text, email) |
| `encoding` | str | Auto | Encodage du fichier |

## Chunking Strategies

### Basic (`chunk_elements`)

Combine les elements sequentiels pour maximiser le remplissage de chaque chunk.
- Respecte `max_characters` (hard limit) et `new_after_n_chars` (soft limit)
- Isole les elements surdimensionnes avant text-splitting
- Ne combine jamais les elements Table avec d'autres

### By Title (`chunk_by_title`)

Preserve les frontieres de sections et optionnellement de pages.
- Ferme le chunk en cours quand un element Title est rencontre
- Respecte les sauts de page si `multipage_sections=False`
- Combine les petites sections sequentielles via `combine_text_under_n_chars`

## Parametres de chunking

| Parametre | Type | Defaut | Applicable a | Description |
|-----------|------|--------|--------------|-------------|
| `chunking_strategy` | str | - | all | "basic" ou "by_title" |
| `max_characters` | int | 500 | all | Hard max par chunk |
| `new_after_n_chars` | int | max_characters | all | Soft max (commence un nouveau chunk) |
| `overlap` | int | 0 | all | Overlap en caracteres (text-splitting only) |
| `overlap_all` | bool | False | all | Overlap entre tous les chunks |
| `combine_text_under_n_chars` | int | max_characters | by_title | Combine petites sections |
| `multipage_sections` | bool | True | by_title | Autoriser sections multi-pages |
| `include_orig_elements` | bool | False | all | Garder elements originaux en metadata |

## Usage

```python
# Partition + chunking integre
from unstructured.partition.auto import partition

elements = partition(
    filename="rapport.pdf",
    strategy="auto",
    languages=["fra", "eng"],
    chunking_strategy="by_title",
    max_characters=2000,
    new_after_n_chars=1500,
    overlap=200,
    combine_text_under_n_chars=500,
    multipage_sections=True,
    include_orig_elements=True,
)

# Partition separee + chunking
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title

elements = partition(filename="rapport.pdf", strategy="hi_res", languages=["fra"])
chunks = chunk_by_title(
    elements,
    max_characters=2000,
    new_after_n_chars=1500,
    overlap=200,
    combine_text_under_n_chars=500,
)
```

## Metadata des elements

Chaque element a :
- `.text` : contenu textuel
- `.category` : type (Title, NarrativeText, Table, ListItem, Image, PageBreak, etc.)
- `.metadata` : dict avec `page_number`, `filename`, `coordinates`, `text_as_html` (tables), etc.

## Defauts recommandes (2026)

- `strategy="auto"` pour usage general
- `strategy="hi_res"` pour PDF complexes avec tables
- `chunking_strategy="by_title"` pour documents structures
- `max_characters=2000`, `new_after_n_chars=1500`, `overlap=200`
- `combine_text_under_n_chars=500`
