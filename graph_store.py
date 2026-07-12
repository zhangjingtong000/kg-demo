"""
graph_store.py — Knowledge graph storage with Neo4j-compatible data model.

Backends:
  - networkx  (lightweight, no server needed)
  - neo4j     (production, requires running Neo4j server)

Usage:
  store = GraphStore(backend="networkx")
  store.import_from_json("test_pipeline.json")
  store.query("MATCH (n:Exercise) RETURN n.name")
"""

import json
from pathlib import Path

# ── NetworkX Backend ─────────────────────────────────────

class NetworkXStore:
    def __init__(self):
        import networkx as nx
        self.g = nx.DiGraph()

    def import_data(self, nodes: list[dict], edges: list[dict]):
        """Import nodes and edges with case-insensitive name matching."""
        # Build case-insensitive lookup
        name_map = {}  # lowercase → canonical name
        for n in nodes:
            canonical = n["name"].strip()
            key = canonical.lower()
            if key in name_map:
                # Keep the Title Case version
                if canonical[0].isupper():
                    name_map[key] = canonical
            else:
                name_map[key] = canonical
            self.g.add_node(
                name_map[key],
                label=n.get("type", "Entity"),
                description=n.get("description", ""),
            )

        for e in edges:
            src_key = e["source"].strip().lower()
            tgt_key = e["target"].strip().lower()
            src = name_map.get(src_key, e["source"].strip())
            tgt = name_map.get(tgt_key, e["target"].strip())
            # Only add edge if both endpoints exist (skip dangling edges)
            if src in self.g and tgt in self.g:
                self.g.add_edge(
                    src, tgt,
                    type=e.get("type", "RELATED_TO"),
                    description=e.get("description", ""),
                )

    def query_nodes(self, label: str = None) -> list[dict]:
        """Return all nodes, optionally filtered by label."""
        result = []
        for name, data in self.g.nodes(data=True):
            if label and data.get("label") != label:
                continue
            result.append({"name": name, **data})
        return result

    def query_edges(self, rel_type: str = None) -> list[dict]:
        """Return all edges, optionally filtered by type."""
        result = []
        for src, tgt, data in self.g.edges(data=True):
            if rel_type and data.get("type") != rel_type:
                continue
            result.append({"source": src, "target": tgt, **data})
        return result

    def get_neighbors(self, node_name: str, depth: int = 1) -> dict:
        """Get a node and its N-hop neighborhood (for subgraph queries)."""
        nodes_set = {node_name}
        edges_list = []
        frontier = {node_name}

        for _ in range(depth):
            next_frontier = set()
            for n in list(frontier):
                for _, tgt, data in self.g.out_edges(n, data=True):
                    edges_list.append({"source": n, "target": tgt, **data})
                    if tgt not in nodes_set:
                        nodes_set.add(tgt)
                        next_frontier.add(tgt)
                for src, _, data in self.g.in_edges(n, data=True):
                    edges_list.append({"source": src, "target": n, **data})
                    if src not in nodes_set:
                        nodes_set.add(src)
                        next_frontier.add(src)
            frontier = next_frontier

        nodes_list = [{"name": n, **self.g.nodes[n]} for n in nodes_set]
        return {"nodes": nodes_list, "edges": edges_list}

    def stats(self) -> dict:
        return {
            "nodes": self.g.number_of_nodes(),
            "edges": self.g.number_of_edges(),
        }


# ── Neo4j Backend (when server is available) ─────────────

class Neo4jStore:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password"):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def import_data(self, nodes: list[dict], edges: list[dict]):
        with self.driver.session() as s:
            # Create nodes
            for n in nodes:
                s.run(
                    f"MERGE (x:{n['type']} {{name: $name}}) SET x.description = $desc",
                    name=n["name"], desc=n.get("description", ""),
                )
            # Create edges
            for e in edges:
                s.run(
                    f"MATCH (a {{name: $src}}), (b {{name: $tgt}}) "
                    f"MERGE (a)-[:{e['type']} {{description: $desc}}]->(b)",
                    src=e["source"], tgt=e["target"], desc=e.get("description", ""),
                )

    def query_nodes(self, label: str = None) -> list[dict]:
        with self.driver.session() as s:
            if label:
                result = s.run(f"MATCH (n:{label}) RETURN n.name, labels(n), n.description")
            else:
                result = s.run("MATCH (n) RETURN n.name, labels(n), n.description")
            return [{"name": r["n.name"], "type": r["labels(n)"][0],
                     "description": r.get("n.description", "")} for r in result]

    def query_edges(self, rel_type: str = None) -> list[dict]:
        with self.driver.session() as s:
            q = "MATCH (a)-[r]->(b)" + (f" WHERE type(r) = '{rel_type}'" if rel_type else "") + " RETURN a.name, b.name, type(r), r.description"
            result = s.run(q)
            return [{"source": r["a.name"], "target": r["b.name"],
                     "type": r["type(r)"], "description": r.get("r.description", "")} for r in result]

    def get_neighbors(self, node_name: str, depth: int = 1) -> dict:
        with self.driver.session() as s:
            result = s.run(
                f"MATCH (a {{name: $name}})-[r*1..{depth}]-(b) "
                "RETURN a, r, b", name=node_name
            )
            # Simplified: collect unique nodes and edges
            nodes_set, edges_list = set(), []
            for record in result:
                nodes_set.add(record["a"]["name"])
                nodes_set.add(record["b"]["name"])
                for rel in record["r"]:
                    edges_list.append({
                        "source": record["a"]["name"],
                        "target": record["b"]["name"],
                        "type": rel.type,
                    })
            return {"nodes": list(nodes_set), "edges": edges_list}

    def stats(self) -> dict:
        with self.driver.session() as s:
            n = s.run("MATCH (n) RETURN count(n)").single()[0]
            e = s.run("MATCH ()-[r]->() RETURN count(r)").single()[0]
        return {"nodes": n, "edges": e}

    def close(self):
        self.driver.close()


# ── Unified Interface ────────────────────────────────────

class GraphStore:
    def __init__(self, backend: str = "networkx", **kwargs):
        if backend == "neo4j":
            self.store = Neo4jStore(**kwargs)
        else:
            self.store = NetworkXStore()

    def import_from_json(self, json_path: str):
        """Import from kg_extractor output JSON."""
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        nodes = data.get("nodes", data.get("result", {}).get("nodes", []))
        edges = data.get("edges", data.get("result", {}).get("edges", []))
        self.store.import_data(nodes, edges)
        return self.store.stats()

    def get_3d_data(self) -> dict:
        """Return data in format ready for 3D visualization."""
        nodes = self.store.query_nodes()
        edges = self.store.query_edges()

        # Generate initial 3D positions using spring layout
        try:
            import networkx as nx
            g = nx.DiGraph()
            for n in nodes:
                g.add_node(n["name"])
            for e in edges:
                g.add_edge(e["source"], e["target"])
            pos = nx.spring_layout(g, dim=3, seed=42)
            for n in nodes:
                p = pos.get(n["name"], [0, 0, 0])
                n["x"], n["y"], n["z"] = float(p[0]), float(p[1]), float(p[2])
        except ImportError:
            for n in nodes:
                n["x"] = n["y"] = n["z"] = 0

        return {"nodes": nodes, "edges": edges, "stats": self.store.stats()}

    def stats(self) -> dict:
        return self.store.stats()


# ── CLI ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    store = GraphStore(backend="networkx")
    path = sys.argv[1] if len(sys.argv) > 1 else "test_pipeline.json"
    stats = store.import_from_json(path)
    print(f"Imported: {stats['nodes']} nodes, {stats['edges']} edges")

    data = store.get_3d_data()
    print(f"3D data: {len(data['nodes'])} nodes with positions, {len(data['edges'])} edges")
