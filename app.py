"""
app.py — FastAPI backend for the KG extraction pipeline.

Endpoints:
  POST /upload       — Upload PDF, run full pipeline, return graph
  GET  /graph/{id}   — Get stored graph
  GET  /stats        — Pipeline statistics

Run:
  python app.py
  uvicorn app:app --reload
"""

import json, os, uuid, shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from pdf_parser import parse_pdf, chunk_document
from kg_extractor import extract_chunk, deduplicate_entities, MODELS
from graph_store import GraphStore

# ── App Setup ────────────────────────────────────────────

app = FastAPI(title="KG Extraction API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Store graphs in memory + on disk
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
graphs: dict[str, dict] = {}  # id → graph data


# ── Models ───────────────────────────────────────────────

class GraphResponse(BaseModel):
    id: str
    nodes: list[dict]
    edges: list[dict]
    stats: dict
    created_at: str

class ChatRequest(BaseModel):
    graph_id: str
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = []


# ── Routes ───────────────────────────────────────────────

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    mode: str = Query("cloud", description="Model backend: cloud or local"),
    max_chars: int = Query(500, description="Max chars per chunk"),
):
    """Upload a PDF, run the full extraction pipeline, return the graph."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files supported")

    # Save uploaded file
    gid = uuid.uuid4().hex[:8]
    upload_dir = DATA_DIR / gid
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / file.filename
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Step 1-2: Parse + chunk
        parsed = parse_pdf(str(pdf_path), str(upload_dir))
        chunked = chunk_document(parsed, max_chars=max_chars)

        # Step 3-4: Extract from each chunk
        model_text = MODELS[mode]["text"]
        model_vis = MODELS[mode]["vision"]
        all_nodes, all_edges = [], []
        total_e_s, total_r_s = 0, 0

        for ch in chunked["chunks"]:
            img_path = ch["images"][0]["path"] if ch["images"] else None
            res = extract_chunk(ch["text"], model_text, mode, model_vis, img_path)
            all_nodes.extend(res["nodes"])
            all_edges.extend(res["edges"])
            total_e_s += res["timing"]["entities_s"]
            total_r_s += res["timing"]["relations_s"]

        # Step 5: Dedup
        all_nodes = deduplicate_entities(all_nodes, mode)
        seen_edges = set()
        deduped_edges = []
        for e in all_edges:
            key = (e["source"].lower(), e["target"].lower(), e["type"].lower())
            if key not in seen_edges:
                seen_edges.add(key)
                deduped_edges.append(e)
        all_edges = deduped_edges

        # Step 6: Store in Neo4j + NetworkX
        store = GraphStore(backend="networkx")
        store.store.import_data(all_nodes, all_edges)
        graph_3d = store.get_3d_data()

        # Save
        result = {
            "id": gid,
            "nodes": graph_3d["nodes"],
            "edges": graph_3d["edges"],
            "stats": {
                "pdf_pages": parsed["total_pages"],
                "chunks": chunked["total_chunks"],
                "nodes": len(all_nodes),
                "edges": len(all_edges),
                "tables": len(chunked.get("tables", [])),
                "extraction_time_s": round(total_e_s + total_r_s, 1),
                "images_found": sum(len(p["images"]) for p in parsed["pages"]),
            },
            "created_at": datetime.now().isoformat(),
        }
        graphs[gid] = result

        # Save to disk
        (upload_dir / "graph.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return JSONResponse(result)

    except Exception as e:
        raise HTTPException(500, f"Pipeline failed: {str(e)}")


@app.get("/graph/{graph_id}")
async def get_graph(graph_id: str):
    """Retrieve a previously extracted graph by ID."""
    if graph_id not in graphs:
        # Try loading from disk
        disk_path = DATA_DIR / graph_id / "graph.json"
        if disk_path.exists():
            graphs[graph_id] = json.loads(disk_path.read_text(encoding="utf-8"))
        else:
            raise HTTPException(404, f"Graph '{graph_id}' not found")
    return graphs[graph_id]


@app.post("/chat")
async def chat(req: ChatRequest):
    """Simple KG-based Q&A (uses Neo4j + LLM for retrieval)."""
    if req.graph_id not in graphs:
        raise HTTPException(404, f"Graph '{req.graph_id}' not found")

    graph = graphs[req.graph_id]
    nodes = {n["name"]: n for n in graph["nodes"]}
    edges = graph["edges"]

    # Simple retrieval: find matching nodes and their neighbors
    q_lower = req.question.lower()
    matched_nodes = [
        n for n in graph["nodes"]
        if any(word in n["name"].lower() or word in n.get("description", "").lower()
               for word in q_lower.split())
    ]

    # Get connected edges
    matched_names = {n["name"] for n in matched_nodes}
    relevant_edges = [
        e for e in edges
        if e["source"] in matched_names or e["target"] in matched_names
    ]

    # Build natural language answer from graph data
    if not matched_nodes:
        answer = "No relevant entities found in the knowledge graph for your question."
    else:
        parts = []
        for e in relevant_edges[:10]:
            parts.append(f"{e['source']} {e['type'].replace('_',' ').lower()} {e['target']}")
        answer = "Based on the knowledge graph:\n" + "\n".join(f"- {p}" for p in parts)

    return ChatResponse(answer=answer, sources=relevant_edges[:10])


@app.get("/stats")
async def stats():
    """Get overall pipeline statistics."""
    return {
        "graphs_stored": len(graphs),
        "total_nodes": sum(len(g["nodes"]) for g in graphs.values()),
        "total_edges": sum(len(g["edges"]) for g in graphs.values()),
    }


# ── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
