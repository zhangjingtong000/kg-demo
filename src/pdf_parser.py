"""
pdf_parser.py — PDF text + image extraction with structure-aware chunking.

Usage:
  python pdf_parser.py input.pdf -o output_dir/
  python pdf_parser.py input.pdf --json  (print JSON to stdout)
"""

import argparse, json, os, sys
from pathlib import Path
from typing import Optional


# ── PDF Parsing ──────────────────────────────────────────

def parse_pdf(pdf_path: str, output_dir: Optional[str] = None) -> dict:
    """
    Extract text and images from a PDF file.

    Returns:
        dict with keys: pages (list of {num, text, images[]})
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    out = {"file": pdf_path, "total_pages": len(doc), "pages": []}

    base = Path(output_dir) if output_dir else Path(pdf_path).parent / "extracted"
    base.mkdir(parents=True, exist_ok=True)

    for pi in range(len(doc)):
        page = doc[pi]
        text = page.get_text("text")  # plain text extraction
        images = []

        # Extract embedded images
        for img_idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            img_ext = base_image["ext"]
            img_name = f"page{pi+1:03d}_img{img_idx+1:02d}.{img_ext}"
            img_path = base / img_name
            img_path.write_bytes(img_bytes)
            images.append({
                "name": img_name,
                "path": str(img_path),
                "ext": img_ext,
                "size": len(img_bytes),
            })

        out["pages"].append({
            "num": pi + 1,
            "text": text.strip(),
            "images": images,
        })

    doc.close()

    # Extract tables using find_tables (simple detection)
    try:
        doc2 = fitz.open(pdf_path)
        tables_out = []
        for pi in range(len(doc2)):
            page = doc2[pi]
            tabs = page.find_tables()
            if tabs and tabs.tables:
                for ti, tab in enumerate(tabs.tables):
                    tables_out.append({
                        "page": pi + 1,
                        "table_idx": ti + 1,
                        "rows": len(tab.row_count) if hasattr(tab, 'row_count') else len(tab.extract()),
                        "data": tab.extract(),
                    })
        doc2.close()
        out["tables"] = tables_out
    except Exception:
        out["tables"] = []

    return out


# ── Chunking ──────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = 500, overlap_ratio: float = 0.3) -> list[str]:
    """
    Structure-aware chunking with sliding window overlap.
    Splits on paragraph boundaries, keeps sections intact.
    """
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                # Split long paragraph by sentences
                sentences = [s.strip() + "." for s in para.replace("!", ".").replace("?", ".").split(".") if s.strip()]
                sub = ""
                for sent in sentences:
                    if len(sub) + len(sent) <= max_chars:
                        sub = (sub + " " + sent).strip() if sub else sent
                    else:
                        if sub: chunks.append(sub)
                        sub = sent
                current = sub if sub else ""
            else:
                current = para

    if current:
        chunks.append(current)

    # Sliding window overlap
    if overlap_ratio > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        overlap_chars = int(max_chars * overlap_ratio)
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            if len(prev) > overlap_chars:
                prefix = prev[-overlap_chars:]
                space_idx = prefix.find(" ")
                if space_idx > 0:
                    prefix = prefix[space_idx:].strip()
                overlapped.append(prefix + "\n\n" + chunks[i])
            else:
                overlapped.append(chunks[i])
        chunks = overlapped

    return chunks


def chunk_document(parsed: dict, max_chars: int = 500, overlap_ratio: float = 0.3) -> dict:
    """Apply chunking to all pages in a parsed document."""
    all_chunks = []
    for page in parsed["pages"]:
        page_chunks = chunk_text(page["text"], max_chars, overlap_ratio)
        for ci, chunk in enumerate(page_chunks):
            all_chunks.append({
                "page": page["num"],
                "chunk_idx": ci + 1,
                "char_count": len(chunk),
                "text": chunk,
                "images": page["images"] if ci == 0 else [],  # images only on first chunk of page
            })

    return {
        "file": parsed["file"],
        "total_pages": parsed["total_pages"],
        "total_chunks": len(all_chunks),
        "tables": parsed.get("tables", []),
        "chunks": all_chunks,
    }


# ── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PDF parser + chunker")
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument("--max-chars", type=int, default=500, help="Max chars per chunk")
    parser.add_argument("--overlap", type=float, default=0.3, help="Overlap ratio")
    parser.add_argument("--no-chunk", action="store_true", help="Skip chunking, output raw text")
    args = parser.parse_args()

    # Parse
    out_dir = args.output or str(Path(args.input).with_suffix("")) + "_extracted"
    parsed = parse_pdf(args.input, out_dir)

    # Chunk
    if args.no_chunk:
        result = {"parsed": parsed}
    else:
        chunked = chunk_document(parsed, args.max_chars, args.overlap)
        result = {"parsed": parsed, "chunked": chunked}

    result["config"] = {
        "max_chars": args.max_chars,
        "overlap_ratio": args.overlap,
        "chunking": not args.no_chunk,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        out_path = Path(out_dir) / "output.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved to {out_path}")
        print(f"  Pages: {parsed['total_pages']}")
        if not args.no_chunk:
            print(f"  Chunks: {chunked['total_chunks']}")
        print(f"  Images extracted to: {out_dir}/")


if __name__ == "__main__":
    main()
