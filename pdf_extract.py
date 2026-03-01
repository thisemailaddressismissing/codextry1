#!/usr/bin/env python3
"""Simple PDF data extraction CLI tool.

Features:
- Extract text from selected pages
- Extract document metadata
- Run regex-based field extraction
- Save output as JSON (default) or plain text
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pypdf import PdfReader


@dataclass
class PatternSpec:
    name: str
    regex: str


def parse_page_spec(spec: Optional[str], total_pages: int) -> List[int]:
    """Parse a page spec like '1-3,5' into zero-based page indices."""
    if not spec:
        return list(range(total_pages))

    pages: set[int] = set()
    for part in spec.split(","):
        chunk = part.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_s, end_s = chunk.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            if start <= 0 or end <= 0:
                raise ValueError("Page numbers must be 1 or greater")
            if end < start:
                raise ValueError(f"Invalid page range '{chunk}': end before start")
            pages.update(range(start - 1, end))
        else:
            page = int(chunk)
            if page <= 0:
                raise ValueError("Page numbers must be 1 or greater")
            pages.add(page - 1)

    invalid = [p + 1 for p in pages if p < 0 or p >= total_pages]
    if invalid:
        raise ValueError(
            f"Page(s) out of range: {invalid}. PDF has {total_pages} pages."
        )
    return sorted(pages)


def parse_pattern(spec: str) -> PatternSpec:
    """Parse a pattern spec in NAME=REGEX form."""
    if "=" not in spec:
        raise ValueError(
            f"Invalid pattern '{spec}'. Use NAME=REGEX format, e.g. invoice=Invoice\\s+#(\\d+)"
        )
    name, regex = spec.split("=", 1)
    name = name.strip()
    regex = regex.strip()
    if not name or not regex:
        raise ValueError(f"Invalid pattern '{spec}'. NAME and REGEX are both required.")
    return PatternSpec(name=name, regex=regex)


def extract_text_by_page(reader: PdfReader, page_indices: Iterable[int]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for idx in page_indices:
        page = reader.pages[idx]
        text = page.extract_text() or ""
        records.append({"page": idx + 1, "text": text})
    return records


def apply_patterns(
    pages: List[Dict[str, Any]], pattern_specs: List[PatternSpec]
) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    for spec in pattern_specs:
        compiled = re.compile(spec.regex, flags=re.MULTILINE)
        matches: List[Dict[str, Any]] = []
        for page in pages:
            text = page["text"]
            for match in compiled.finditer(text):
                groups: Any
                if match.groups():
                    groups = list(match.groups())
                else:
                    groups = [match.group(0)]
                matches.append(
                    {
                        "page": page["page"],
                        "match": match.group(0),
                        "groups": groups,
                    }
                )
        results[spec.name] = {
            "regex": spec.regex,
            "count": len(matches),
            "matches": matches,
            "first": matches[0] if matches else None,
        }
    return results


def build_output(
    source: Path,
    pages: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    pattern_results: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "source": str(source),
        "page_count": len(pages),
        "metadata": metadata,
        "pages": pages,
    }
    if pattern_results is not None:
        payload["patterns"] = pattern_results
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="PDF data extraction tool")
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("-o", "--output", type=Path, help="Output file path")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--pages",
        help="Pages to extract, e.g. '1-3,5'. Defaults to all pages.",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        default=[],
        help="Regex pattern in NAME=REGEX format. Can be used multiple times.",
    )

    args = parser.parse_args()

    if not args.pdf.exists():
        parser.error(f"Input file does not exist: {args.pdf}")

    reader = PdfReader(str(args.pdf))

    try:
        page_indices = parse_page_spec(args.pages, len(reader.pages))
    except ValueError as exc:
        parser.error(str(exc))

    pages = extract_text_by_page(reader, page_indices)
    metadata = {k.lstrip("/"): v for k, v in (reader.metadata or {}).items()}

    pattern_specs: List[PatternSpec] = []
    for raw in args.pattern:
        try:
            pattern_specs.append(parse_pattern(raw))
        except ValueError as exc:
            parser.error(str(exc))

    pattern_results = apply_patterns(pages, pattern_specs) if pattern_specs else None

    if args.format == "json":
        output_text = json.dumps(
            build_output(args.pdf, pages, metadata, pattern_results),
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    else:
        text_chunks = [f"# {args.pdf}"]
        for page in pages:
            text_chunks.append(f"\n## Page {page['page']}\n")
            text_chunks.append(page["text"])
        output_text = "\n".join(text_chunks)

    if args.output:
        args.output.write_text(output_text, encoding="utf-8")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
