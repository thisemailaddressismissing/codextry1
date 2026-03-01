# PDF Data Extraction Tool

A lightweight command-line tool to extract structured data from PDF files.

## Features

- Extract text from all pages or a selected page range
- Extract PDF metadata
- Run custom regex-based field extraction
- Output results as JSON (default) or plain text

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Basic extraction (JSON to stdout)

```bash
python pdf_extract.py input.pdf
```

### Extract specific pages and write to file

```bash
python pdf_extract.py input.pdf --pages "1-3,5" -o output.json
```

### Extract fields with regex patterns

```bash
python pdf_extract.py invoice.pdf \
  --pattern "invoice_number=Invoice\\s*#\\s*(\\w+)" \
  --pattern "total=Total\\s*:\\s*\\$?([0-9.,]+)"
```

### Plain text output

```bash
python pdf_extract.py input.pdf --format text -o extracted.txt
```

## Output schema (JSON)

- `source`: input PDF path
- `page_count`: number of extracted pages
- `metadata`: normalized PDF metadata
- `pages`: list of `{ page, text }`
- `patterns` (optional): per-pattern match info (`count`, `matches`, `first`)

## Notes

- Scanned/image-only PDFs require OCR before text extraction.
- Regex patterns use Python's `re` syntax with multiline mode enabled.
