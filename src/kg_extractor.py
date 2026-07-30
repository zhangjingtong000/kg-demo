"""
kg_extractor.py — LLM-powered entity & relationship extraction

Supports:
  - Local:  Ollama (text: qwen3.5:9b, vision: qwen3-vl:4b)
  - Cloud:  SiliconFlow API (text: Qwen3-32B, vision: Qwen3-VL-32B)
            DeepSeek via any OpenAI-compatible endpoint

Usage:
  python kg_extractor.py --text "Squats target quadriceps..." --mode local
  python kg_extractor.py --file sample.txt --mode cloud --compare
"""

import argparse, json, os, sys, time, base64
from pathlib import Path
from typing import Optional

# ── Config ──────────────────────────────────────────────
SF_API_KEY = os.environ.get("SF_API_KEY", "")
SF_BASE   = "https://api.siliconflow.cn/v1"
DS_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_BASE   = "https://api.deepseek.com/v1"
OLLAMA    = "http://localhost:11434"

MODELS = {
    "local": {
        "text":   "qwen3.5:9b",
        "vision": "qwen3-vl:4b",
    },
    "cloud": {
        "text":   "deepseek-chat",       # DeepSeek-V3, fast + cheap
        "vision": "Qwen/Qwen3-VL-32B-Instruct",  # via SiliconFlow for images
    },
    "ds": {
        "text":   "deepseek-chat",
        "vision": None,  # DeepSeek doesn't have vision API
    },
}

# ── Prompt Templates ─────────────────────────────────────
ENTITY_TYPES = [
    "Exercise", "Muscle", "Equipment", "BodyPart",
    "Concept", "Metric", "Person", "Organization",
]

RELATION_TYPES = [
    "TRAINS", "USES", "PART_OF", "SYNERGIST",
    "OPPOSES", "PREREQUISITE", "LOCATED_AT", "RELATED_TO",
]

ENTITY_PROMPT = """---Role---
You are a Knowledge Graph Specialist. Extract all entities from the text.

---Rules---
1. Only extract entities EXPLICITLY mentioned. Do not infer or imagine.
2. Entity names in Title Case, consistent across the text.
3. Use third person only.
4. Output format (one per line, NO markdown, NO JSON):
   entity<|>EntityName<|>EntityType<|>Brief description

---Entity Types---
Use ONLY these types: {entity_types}

---Text---
{text}

---Output---
Output all entities, then <|COMPLETE|> on the final line."""

RELATION_PROMPT = """---Role---
You are a Knowledge Graph Specialist. Now extract relationships between the given entities.

---Entities---
{entity_list}

---Rules---
1. Only connect entities that have a direct, explicit relationship.
2. Decompose multi-entity relationships into binary pairs.
3. Use ONLY these relationship types: {relation_types}
4. Output format (one per line, NO markdown, NO JSON):
   relation<|>SourceEntity<|>TargetEntity<|>RelationType<|>Brief explanation

---Text (for context)---
{text}

---Output---
Output all relationships, then <|COMPLETE|> on the final line."""


# ── Backend Adapters ─────────────────────────────────────

def call_ollama(model: str, prompt: str, image_path: Optional[str] = None) -> str:
    """Call local Ollama model."""
    import requests
    payload = {"model": model, "prompt": prompt, "stream": False,
               "options": {"temperature": 0.1, "num_predict": 2048, "enable_thinking": False}}
    if image_path:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        payload["images"] = [img_b64]
    r = requests.post(f"{OLLAMA}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("response") or data.get("thinking", "")


def call_siliconflow(model: str, prompt: str, image_path: Optional[str] = None) -> str:
    """Call SiliconFlow API (OpenAI-compatible). Used for vision models."""
    return call_openai_compat(SF_BASE, SF_API_KEY, model, prompt, image_path)


def call_deepseek(model: str, prompt: str) -> str:
    """Call DeepSeek official API."""
    return call_openai_compat(DS_BASE, DS_API_KEY, model, prompt, None)


def call_openai_compat(base_url: str, api_key: str, model: str, prompt: str,
                       image_path: Optional[str] = None) -> str:
    """Call any OpenAI-compatible API."""
    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if image_path:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        messages = [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}]
    else:
        messages = [{"role": "user", "content": prompt}]
    payload = {"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 2048}
    r = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    return msg.get("content", "")


def call_openai_compatible(base_url: str, api_key: str, model: str, prompt: str) -> str:
    """Call any OpenAI-compatible API (DeepSeek, etc.)."""
    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.1, "max_tokens": 2048}
    r = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_openai_compatible(base_url: str, api_key: str, model: str, prompt: str) -> str:
    """Call any OpenAI-compatible API (DeepSeek, etc.)."""
    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.1, "max_tokens": 2048}
    r = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ── Parsing ──────────────────────────────────────────────

def parse_entities(raw: str) -> list[dict]:
    """Parse entity lines into structured list. Handles both:
    'entity<|>Name<|>Type<|>Desc' and 'Name<|>Type<|>Desc'."""
    entities = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or "<|COMPLETE|>" in line:
            continue
        # Strip optional entity prefix
        if line.startswith("entity<|>"):
            line = line[len("entity<|>"):]
        parts = line.split("<|>")
        if len(parts) >= 3:
            entities.append({
                "name": parts[0].strip(),
                "type": parts[1].strip(),
                "description": parts[2].strip() if len(parts) >= 3 else "",
            })
    return entities


def parse_relations(raw: str) -> list[dict]:
    """Parse relation lines. Auto-detects field order (some models swap src/target/type)."""
    relations = []
    known_types = {t.lower() for t in RELATION_TYPES}

    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or "<|COMPLETE|>" in line:
            continue
        if line.startswith("relation<|>"):
            line = line[len("relation<|>"):]
        parts = [p.strip() for p in line.split("<|>")]
        if len(parts) < 4:
            continue

        # Detect field order: if parts[0] looks like a relation type, reorder
        if parts[0].lower() in known_types:
            # Model output: Type<|>Source<|>Target<|>Desc
            relations.append({
                "source": parts[1],
                "target": parts[2],
                "type": parts[0],
                "description": parts[3] if len(parts) > 3 else "",
            })
        else:
            # Expected: Source<|>Target<|>Type<|>Desc
            relations.append({
                "source": parts[0],
                "target": parts[1],
                "type": parts[2],
                "description": parts[3] if len(parts) > 3 else "",
            })
    return relations


# ── Chunking ──────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = 500, overlap_ratio: float = 0.3) -> list[str]:
    """
    Structure-aware chunking with sliding window overlap.

    - Splits on paragraph/sentence boundaries
    - Keeps paragraphs intact when possible
    - Overlap: last N chars of previous chunk prepended to next chunk
    - Falls back to sentence splitting for very long paragraphs
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        # If adding this paragraph fits, do it
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip() if current else para
        else:
            # Current chunk is full → save it
            if current:
                chunks.append(current)
            # If this paragraph alone is too long, split by sentences
            if len(para) > max_chars:
                sentences = [s.strip() + "." for s in para.replace("!", ".").replace("?", ".").split(".") if s.strip()]
                sub = ""
                for sent in sentences:
                    if len(sub) + len(sent) <= max_chars:
                        sub = (sub + " " + sent).strip() if sub else sent
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = sent
                if sub:
                    current = sub
                else:
                    current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    # Apply sliding window overlap
    if overlap_ratio > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        overlap_chars = int(max_chars * overlap_ratio)
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            if len(prev) > overlap_chars:
                prefix = prev[-overlap_chars:]
                # Start overlap at a word boundary
                space_idx = prefix.find(" ")
                if space_idx > 0:
                    prefix = prefix[space_idx:].strip()
                overlapped.append(prefix + "\n\n" + chunks[i])
            else:
                overlapped.append(chunks[i])
        chunks = overlapped

    return chunks


def deduplicate_entities(entities: list[dict], mode: str = "local") -> list[dict]:
    """
    Merge entities with identical or similar names.
    - Case-insensitive exact name → merge (keep longer description)
    - Same type + >70% char overlap → merge
    - Cross-type: keep separate (e.g. "Bench Press" exercise vs "Bench" equipment)
    """
    # Phase 1: Case-insensitive exact name dedup
    seen = {}
    for e in entities:
        key = e["name"].lower().strip()
        if key in seen:
            existing = seen[key]
            # Normalize to Title Case
            if e["name"] and existing["name"] and e["name"][0].isupper() and not existing["name"][0].isupper():
                existing["name"] = e["name"]
            # Keep longer description
            if len(e.get("description", "")) > len(existing.get("description", "")):
                existing["description"] = e["description"]
        else:
            e["name"] = e["name"].strip()
            seen[key] = e

    unique = list(seen.values())
    if len(unique) <= 1:
        return unique

    # Phase 2: Same-type fuzzy dedup
    by_type = {}
    for e in unique:
        t = e["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(e)

    merged = []
    for t, group in by_type.items():
        if len(group) <= 1:
            merged.extend(group)
            continue
        names = [e["name"] for e in group]
        duplicates = set()
        for i in range(len(names)):
            if i in duplicates: continue
            for j in range(i+1, len(names)):
                if j in duplicates: continue
                ni, nj = names[i].lower(), names[j].lower()
                # One contains the other, or high char overlap
                if ni in nj or nj in ni or _char_overlap(ni, nj) > 0.7:
                    duplicates.add(j)
        for i, e in enumerate(group):
            if i not in duplicates:
                merged.append(e)

    return merged


def _char_overlap(a: str, b: str) -> float:
    """Simple character-level overlap ratio."""
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    return len(intersection) / min(len(set_a), len(set_b))


# ── Pipeline ─────────────────────────────────────────────

def extract_chunk(chunk_text: str, model_text: str, mode: str, model_vis: str = None,
                  image_path: Optional[str] = None) -> dict:
    """Extract entities + relations from a single text chunk."""
    # Image context
    full_text = chunk_text
    if image_path:
        t0 = time.time()
        prompt_img = "Describe this image in detail. Focus on any entities, labels, data, or relationships visible."
        img_context = call_ollama(model_vis, prompt_img, image_path) if mode == "local" \
                 else call_siliconflow(model_vis, prompt_img, image_path)
        full_text = chunk_text + "\n\n---Image Context---\n" + img_context
        print(f"    [vision] {model_vis}  ({time.time()-t0:.1f}s)")

    # Phase 1: Entities
    t1 = time.time()
    ep = ENTITY_PROMPT.format(entity_types=", ".join(ENTITY_TYPES), text=full_text)
    raw_entities = call_ollama(model_text, ep) if mode == "local" \
              else call_deepseek(model_text, ep)
    entities = parse_entities(raw_entities)
    dt1 = time.time() - t1
    print(f"    [entities] {len(entities)} entities ({dt1:.1f}s)")
    if len(entities) == 0:
        print(f"    [DEBUG] {raw_entities[:200]}...")

    # Phase 2: Relations
    t2 = time.time()
    entity_names = [e["name"] for e in entities]
    if not entity_names:
        return {"nodes": entities, "edges": [], "timing": {"entities_s": dt1, "relations_s": 0}}

    rp = RELATION_PROMPT.format(
        entity_list="\n".join(f"- {n}" for n in entity_names),
        relation_types=", ".join(RELATION_TYPES),
        text=full_text,
    )
    raw_relations = call_ollama(model_text, rp) if mode == "local" \
                else call_deepseek(model_text, rp)
    relations = parse_relations(raw_relations)
    dt2 = time.time() - t2
    print(f"    [relations] {len(relations)} relations ({dt2:.1f}s)")

    return {"nodes": entities, "edges": relations, "timing": {"entities_s": dt1, "relations_s": dt2}}


def extract(text: str, mode: str = "local", image_path: Optional[str] = None,
            max_chunk_chars: int = 500) -> dict:
    """Run full pipeline: chunk → extract per chunk → merge → dedup → global relations."""
    model_text = MODELS[mode]["text"]
    model_vis = MODELS[mode]["vision"]

    # Chunk long text
    chunks = chunk_text(text, max_chars=max_chunk_chars)
    use_chunking = len(chunks) > 1
    if use_chunking:
        print(f"  [chunking] {len(text)} chars → {len(chunks)} chunks")

    all_nodes = []
    all_edges = []
    total_e_s, total_r_s = 0, 0

    for ci, chunk in enumerate(chunks):
        prefix = f"  [chunk {ci+1}/{len(chunks)}] " if use_chunking else "  "
        print(f"{prefix}{len(chunk)} chars")
        res = extract_chunk(chunk, model_text, mode, model_vis, image_path)
        all_nodes.extend(res["nodes"])
        all_edges.extend(res["edges"])
        total_e_s += res["timing"]["entities_s"]
        total_r_s += res["timing"]["relations_s"]

    # Deduplicate
    if use_chunking:
        before_n = len(all_nodes)
        before_e = len(all_edges)
        all_nodes = deduplicate_entities(all_nodes, mode)
        # Dedup edges: same src/tgt/type → keep one
        seen_edges = set()
        deduped_edges = []
        for e in all_edges:
            key = (e["source"].lower(), e["target"].lower(), e["type"].lower())
            if key not in seen_edges:
                seen_edges.add(key)
                deduped_edges.append(e)
        all_edges = deduped_edges
        print(f"  [dedup] nodes: {before_n}→{len(all_nodes)}, edges: {before_e}→{len(all_edges)}")

    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "timing": {"entities_s": round(total_e_s, 1), "relations_s": round(total_r_s, 1)},
        "model": mode,
        "model_text": model_text,
        "model_vision": model_vis if image_path else None,
        "chunks": len(chunks),
    }


def extract_from_pdf(pdf_path: str, mode: str = "cloud", max_chunk_chars: int = 500) -> dict:
    """Full pipeline: PDF → parse → chunk → extract → merge → JSON."""
    from pdf_parser import parse_pdf, chunk_document

    print(f"Parsing PDF: {pdf_path}")
    parsed = parse_pdf(pdf_path)
    chunked = chunk_document(parsed, max_chars=max_chunk_chars)

    print(f"  {parsed['total_pages']} pages, {chunked['total_chunks']} chunks\n")

    all_nodes = []
    all_edges = []
    total_e_s, total_r_s = 0, 0

    for ch in chunked["chunks"]:
        print(f"  [chunk {ch['chunk_idx']}/{chunked['total_chunks']}] page {ch['page']}, {ch['char_count']} chars")
        # Use first image on the page for vision context (if any)
        img_path = ch["images"][0]["path"] if ch["images"] else None
        res = extract_chunk(ch["text"], MODELS[mode]["text"], mode, MODELS[mode]["vision"], img_path)
        all_nodes.extend(res["nodes"])
        all_edges.extend(res["edges"])
        total_e_s += res["timing"]["entities_s"]
        total_r_s += res["timing"]["relations_s"]

    # Deduplicate
    before_n, before_e = len(all_nodes), len(all_edges)
    all_nodes = deduplicate_entities(all_nodes, mode)
    seen_edges = set()
    deduped_edges = []
    for e in all_edges:
        key = (e["source"].lower(), e["target"].lower(), e["type"].lower())
        if key not in seen_edges:
            seen_edges.add(key)
            deduped_edges.append(e)
    all_edges = deduped_edges
    print(f"\n  [dedup] nodes: {before_n}→{len(all_nodes)}, edges: {before_e}→{len(all_edges)}")

    return {
        "source": pdf_path,
        "nodes": all_nodes,
        "edges": all_edges,
        "timing": {"entities_s": round(total_e_s, 1), "relations_s": round(total_r_s, 1)},
        "model": mode,
        "model_text": MODELS[mode]["text"],
        "chunks": chunked["total_chunks"],
        "tables_found": len(chunked.get("tables", [])),
    }


# ── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="KG Entity & Relation Extractor")
    parser.add_argument("--text", help="Input text to extract from")
    parser.add_argument("--file", help="Input text file path")
    parser.add_argument("--pdf", help="Input PDF file path (full pipeline)")
    parser.add_argument("--image", help="Optional image file for multimodal extraction")
    parser.add_argument("--mode", choices=["local", "cloud"], default="cloud",
                        help="Model backend (default: cloud)")
    parser.add_argument("--compare", action="store_true",
                        help="Run both local and cloud and compare results")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--max-chars", type=int, default=500,
                        help="Max chars per chunk (default: 500)")
    args = parser.parse_args()

    # PDF mode
    if args.pdf:
        result = extract_from_pdf(args.pdf, args.mode, args.max_chars)
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(output_json, encoding="utf-8")
            print(f"\nSaved to {args.output}")
        else:
            print(f"\n── RESULT ({len(result['nodes'])} nodes, {len(result['edges'])} edges) ──")
            print(json.dumps({"nodes": result["nodes"][:5], "edges": result["edges"][:5], "...": f"({len(result['nodes'])} total)"}, ensure_ascii=False, indent=2))
        return

    # Load text
    text = args.text
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")

    if not text or len(text.strip()) < 10:
        print("Error: need --text, --file, or --pdf")
        sys.exit(1)

    print(f"Input: {len(text)} chars")
    print()

    if args.compare:
        results = {}
        for mode in ["local", "cloud"]:
            print(f"── {mode.upper()} ──")
            try:
                results[mode] = extract(text, mode, args.image)
                print()
            except Exception as e:
                print(f"  FAILED: {e}\n")
                results[mode] = {"error": str(e)}

        # Comparison summary
        print("══ COMPARISON ══")
        for mode, r in results.items():
            if "error" in r:
                print(f"  {mode}: ERROR — {r['error']}")
            else:
                t = r["timing"]
                print(f"  {mode}: {len(r['nodes'])} entities, {len(r['edges'])} relations, "
                      f"{t['entities_s']}s + {t['relations_s']}s = {t['entities_s']+t['relations_s']}s")
    else:
        results = extract(text, args.mode, args.image, args.max_chars)

    # Output
    output_json = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"\nSaved to {args.output}")
    else:
        print(f"\n── RESULT ──")
        print(output_json)


if __name__ == "__main__":
    main()
