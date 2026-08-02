# 多尺度知识图谱基础实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为多尺度「语义 / 来源」探索建立可追溯的数据契约、来源证据和稳定 API，不改变现有精细 3D 图谱的默认行为。

**Architecture:** 先在 PDF 抽取流程中保留每个实体和关系来自哪个来源、页码与文本块；再由一个纯 Python 视图模型模块从真实图数据生成来源摘要与详细图推荐窗口。FastAPI 将该视图模型通过独立接口提供给后续宏观前端。语义星云可视化放在后续计划中，避免用合成压测数据决定主题结构。

**Tech Stack:** Python 3.13、FastAPI、Pydantic、NetworkX、pytest；现有原生 HTML/Three.js 仅作为后续消费者。

---

## 文件边界

| 文件 | 职责 |
|---|---|
| `src/explorer_models.py` | 来源、证据、详细阅读窗口的数据模型和纯函数 |
| `src/kg_extractor.py` | 为单个文本块产生的实体和关系写入块级证据 |
| `src/graph_store.py` | 在 NetworkX 图中保留实体与关系的证据列表 |
| `src/app.py` | 保存来源元数据并提供只读探索接口 |
| `tests/test_explorer_models.py` | 纯函数、排序和 80 节点预算的回归测试 |
| `tests/test_explorer_api.py` | FastAPI 来源与探索接口的集成测试 |

## Task 1：定义可追溯探索数据模型

**Files:**

- Create: `src/explorer_models.py`
- Create: `tests/test_explorer_models.py`

- [ ] **Step 1: 写入失败测试，约束 80 节点推荐窗口与来源聚合**

```python
from explorer_models import build_detail_window, build_source_summary

def test_detail_window_keeps_core_then_bridge_then_relevance():
    nodes = [
        {"id": "core", "importance": 9, "bridge_score": 0, "relevance": 0},
        {"id": "bridge", "importance": 1, "bridge_score": 8, "relevance": 0},
        {"id": "search", "importance": 1, "bridge_score": 0, "relevance": 7},
    ] + [{"id": f"n{i}", "importance": 0, "bridge_score": 0, "relevance": 0} for i in range(100)]

    window = build_detail_window(nodes, limit=80)

    assert window["visible_count"] == 80
    assert [node["id"] for node in window["nodes"][:3]] == ["core", "bridge", "search"]
    assert window["total_count"] == 103

def test_source_summary_counts_unique_pages_and_representatives():
    summary = build_source_summary("paper-1", "paper.pdf", [
        {"name": "A", "importance": 6, "evidence": [{"page": 1}]},
        {"name": "B", "importance": 5, "evidence": [{"page": 1}, {"page": 2}]},
    ])

    assert summary["source_id"] == "paper-1"
    assert summary["entity_count"] == 2
    assert summary["page_count"] == 2
    assert [item["name"] for item in summary["representatives"]] == ["A", "B"]
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_explorer_models.py -q`

Expected: `ModuleNotFoundError: No module named 'explorer_models'`。

- [ ] **Step 3: 实现纯数据模型**

在 `src/explorer_models.py` 实现：

```python
def score_node(node: dict) -> tuple[float, float, float, str]:
    return (
        -float(node.get("importance", 0)),
        -float(node.get("bridge_score", 0)),
        -float(node.get("relevance", 0)),
        str(node["id"]),
    )

def build_detail_window(nodes: list[dict], limit: int = 80) -> dict:
    ranked = sorted(nodes, key=score_node)
    return {"nodes": ranked[:limit], "visible_count": min(len(ranked), limit), "total_count": len(ranked)}

def build_source_summary(source_id: str, source_name: str, nodes: list[dict]) -> dict:
    pages = {ref["page"] for node in nodes for ref in node.get("evidence", []) if ref.get("page") is not None}
    representatives = sorted(nodes, key=lambda node: (-float(node.get("importance", 0)), node["name"]))[:3]
    return {"source_id": source_id, "source_name": source_name, "entity_count": len(nodes), "page_count": len(pages), "representatives": representatives}
```

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m pytest tests/test_explorer_models.py -q`

Expected: `2 passed`。

- [ ] **Step 5: 提交**

```powershell
git add src/explorer_models.py tests/test_explorer_models.py
git commit -m "feat: add explorer view-model foundation"
```

## Task 2：在抽取和存储过程中保留页码证据

**Files:**

- Modify: `src/app.py:83-107`
- Modify: `src/graph_store.py:17-60`
- Modify: `tests/test_explorer_api.py`

- [ ] **Step 1: 写入失败的端到端数据保留测试**

```python
from graph_store import NetworkXStore

def test_import_data_merges_node_and_edge_evidence():
    store = NetworkXStore()
    store.import_data(
        [{"name": "Squat", "evidence": [{"source_id": "g1", "page": 3, "chunk_idx": 2}]}],
        [],
    )
    node = store.query_nodes()[0]
    assert node["evidence"] == [{"source_id": "g1", "page": 3, "chunk_idx": 2}]
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_explorer_api.py::test_import_data_merges_node_and_edge_evidence -q`

Expected: `KeyError: 'evidence'`。

- [ ] **Step 3: 在上传循环中附加块级证据，并在去重时合并证据**

为每个 `extract_chunk()` 返回的实体和关系附加同一条证据：

```python
evidence = {
    "source_id": gid,
    "source_name": file.filename,
    "page": ch["page"],
    "chunk_idx": ch["chunk_idx"],
    "text": ch["text"],
}
for node in res["nodes"]:
    node.setdefault("evidence", []).append(evidence)
for edge in res["edges"]:
    edge.setdefault("evidence", []).append(evidence)
```

将当前按名称和关系三元组的去重逻辑改为：保留一个规范对象，同时按 `source_id + page + chunk_idx` 去重合并 `evidence`。在 `NetworkXStore.import_data()` 中把合并后的 `evidence` 写入节点和关系属性；`query_nodes()`、`query_edges()` 原样返回该字段。

- [ ] **Step 4: 运行相关测试并确认通过**

Run: `python -m pytest tests/test_explorer_api.py tests/test_explorer_models.py -q`

Expected: 所有测试通过。

- [ ] **Step 5: 提交**

```powershell
git add src/app.py src/graph_store.py tests/test_explorer_api.py
git commit -m "feat: preserve source evidence in graph data"
```

## Task 3：提供来源摘要与详细阅读窗口 API

**Files:**

- Modify: `src/app.py:142-152`
- Modify: `tests/test_explorer_api.py`

- [ ] **Step 1: 写入失败的接口测试**

```python
from fastapi.testclient import TestClient
from app import app, graphs

client = TestClient(app)

def seed_graph(nodes: int) -> str:
    graph_id = "test-graph"
    graphs[graph_id] = {
        "id": graph_id,
        "source": {"id": graph_id, "name": "fixture.pdf", "kind": "pdf"},
        "nodes": [{"name": f"Entity {index}", "evidence": [{"page": 1}]} for index in range(nodes)],
        "edges": [{"source": "Entity 0", "target": f"Entity {index}"} for index in range(1, nodes)],
    }
    return graph_id

def test_explorer_endpoint_exposes_source_summary_and_80_node_window():
    graph_id = seed_graph(nodes=81)

    response = client.get(f"/graph/{graph_id}/explorer?limit=80")

    assert response.status_code == 200
    body = response.json()
    assert body["detail_window"]["visible_count"] == 80
    assert body["detail_window"]["total_count"] == 81
    assert body["sources"][0]["source_id"] == graph_id
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_explorer_api.py::test_explorer_endpoint_exposes_source_summary_and_80_node_window -q`

Expected: `404 Not Found`。

- [ ] **Step 3: 实现只读探索接口**

在 `src/app.py` 添加：

```python
from collections import Counter

@app.get("/graph/{graph_id}/explorer")
async def get_explorer_graph(graph_id: str, limit: int = Query(80, ge=1, le=500)):
    graph = await get_graph(graph_id)
    degree = Counter(endpoint for edge in graph["edges"] for endpoint in (edge["source"], edge["target"]))
    nodes = [
        {"id": node["name"], "name": node["name"], "importance": degree[node["name"]],
         "bridge_score": node.get("bridge_score", 0), "relevance": 0,
         "evidence": node.get("evidence", [])}
        for node in graph["nodes"]
    ]
    return {
        "graph_id": graph_id,
        "sources": [build_source_summary(graph_id, graph["source"]["name"], nodes)],
        "detail_window": build_detail_window(nodes, limit),
    }
```

同时将保存的图结果补充 `source: {"id": gid, "name": file.filename, "kind": "pdf"}`。若旧图缺少 `source`，返回 `kind: "unknown"` 与图 ID 作为回退来源名，不抛出异常。

- [ ] **Step 4: 运行接口和现有后端测试**

Run: `python -m pytest tests/test_explorer_api.py tests/test_explorer_models.py -q`

Expected: 所有测试通过。

- [ ] **Step 5: 手动验证真实响应**

Run: `uvicorn src.app:app --reload --port 8000`

在已存在的图 ID 上请求：`GET http://127.0.0.1:8000/graph/<graph_id>/explorer?limit=80`。

Expected: 响应包含 `sources`、块级 `evidence` 与 `detail_window`；默认窗口不超过 80 个节点。

- [ ] **Step 6: 提交**

```powershell
git add src/app.py tests/test_explorer_api.py
git commit -m "feat: expose explorer source and detail views"
```

## Task 4：记录后续阶段接口边界

**Files:**

- Modify: `docs/ROADMAP.md`
- Modify: `docs/prd/multiscale-knowledge-graph-exploration.md`

- [ ] **Step 1: 记录本阶段已交付与后续依赖**

在路线图中增加「多尺度探索」条目，并明确：本计划只交付真实来源证据、来源摘要和 80 节点推荐窗口；语义主题命名、星云布局、来源集合视图、右上角范围控件和 Three.js 转场属于后续独立前端计划。

- [ ] **Step 2: 校验文档内容与工作区**

Run: `git diff --check`

Expected: 无输出。

- [ ] **Step 3: 提交**

```powershell
git add docs/ROADMAP.md docs/prd/multiscale-knowledge-graph-exploration.md
git commit -m "docs: stage multiscale explorer rollout"
```

## 计划自检

- PRD 的来源可追溯、推荐 80 节点、全量真实数和子星云前提，分别由 Task 1 至 Task 3 建立数据基础。
- 语义星云、来源集合可视化、切换器与转场未被误写为本阶段完成项，避免在无真实主题数据时构造视觉结论。
- 所有新接口字段在 Task 1 定义、Task 2 写入、Task 3 消费，名称一致。
- 未使用「TODO」「TBD」或未定义的实现步骤。
