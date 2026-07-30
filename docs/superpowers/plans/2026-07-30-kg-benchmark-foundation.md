# KG Benchmark Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure the current liquid-glass KG renderer under deterministic graph sizes without changing the showcase page or its dynamic label behavior.

**Architecture:** A standalone `web/benchmark/` page generates seeded graphs and records browser frame-time percentiles, long tasks and renderer counters. `web/index3d-bounce.html` remains untouched in this phase and is treated as a visual regression reference.

**Tech Stack:** ES modules, Three.js 0.160, `PerformanceObserver`, `requestAnimationFrame`, Node built-in test runner, Playwright CLI.

---

## File map

| Path | Responsibility |
|---|---|
| `web/benchmark/lib/seeded-rng.mjs` | Stable pseudo-random generator. |
| `web/benchmark/lib/graph-fixtures.mjs` | Deterministic clustered node and edge fixtures. |
| `web/benchmark/lib/metrics.mjs` | Frame sampling, percentile summaries and long-task recording. |
| `web/benchmark/lib/benchmark-scene.mjs` | Disposable Three.js high-fidelity baseline scene. |
| `web/benchmark/index.html` | Manual scenario controls and report display. |
| `web/benchmark/test/*.test.mjs` | Node tests for deterministic data and metrics. |
| `docs/PERFORMANCE_RESULTS.md` | Measured, not estimated, result table. |

### Task 1: Seeded fixture generator

**Files:**
- Create: `web/benchmark/lib/seeded-rng.mjs`
- Create: `web/benchmark/lib/graph-fixtures.mjs`
- Test: `web/benchmark/test/graph-fixtures.test.mjs`

- [ ] **Step 1: Write failing fixture tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { createFixture, FIXTURE_PROFILES } from '../lib/graph-fixtures.mjs';

test('fixtures are deterministic', () => {
  assert.deepEqual(createFixture('localDense', 42), createFixture('localDense', 42));
});

test('edges reference distinct existing nodes', () => {
  const fixture = createFixture('communityBrowse', 42);
  const ids = new Set(fixture.nodes.map((node) => node.id));
  fixture.edges.forEach((edge) => {
    assert.ok(ids.has(edge.source));
    assert.ok(ids.has(edge.target));
    assert.notEqual(edge.source, edge.target);
  });
});

test('profile counts match generated data', () => {
  Object.entries(FIXTURE_PROFILES).forEach(([name, profile]) => {
    const fixture = createFixture(name, 42);
    assert.equal(fixture.nodes.length, profile.nodes);
    assert.equal(fixture.edges.length, profile.edges);
  });
});
```

- [ ] **Step 2: Confirm the tests fail**

Run: `node --test web/benchmark/test/graph-fixtures.test.mjs`
Expected: FAIL because the fixture module does not exist.

- [ ] **Step 3: Implement fixtures**

```js
export const FIXTURE_PROFILES = Object.freeze({
  legacy: { nodes: 26, edges: 55, communities: 4 },
  localDense: { nodes: 80, edges: 320, communities: 6 },
  communityBrowse: { nodes: 250, edges: 1200, communities: 12 },
  macroOverview: { nodes: 1000, edges: 5000, communities: 35 },
  stressAggregate: { nodes: 5000, edges: 20000, communities: 100 },
});

export function createFixture(profileName, seed = 20260730) {
  // Return nodes: { id, label, type, community, x, y, z, importance }
  // and deduplicated edges: { id, source, target, type, weight }.
  // Create each community's connected spine before adding cross-community edges.
}
```

Use a seeded 32-bit PRNG and six fixed types: `Concept`, `Method`, `Evidence`, `Author`, `Metric`, `Community`. Nodes must use community-aware positions rather than a uniformly random cube.

- [ ] **Step 4: Verify and commit**

Run: `node --test web/benchmark/test/graph-fixtures.test.mjs`
Expected: three PASS results.

```bash
git add web/benchmark/lib/seeded-rng.mjs web/benchmark/lib/graph-fixtures.mjs web/benchmark/test/graph-fixtures.test.mjs
git commit -m "feat: add deterministic KG benchmark fixtures"
```

### Task 2: Frame metrics collector

**Files:**
- Create: `web/benchmark/lib/metrics.mjs`
- Test: `web/benchmark/test/metrics.test.mjs`

- [ ] **Step 1: Write failing metrics tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { percentile, summarizeFrames } from '../lib/metrics.mjs';

test('percentile uses sorted linear interpolation', () => {
  assert.equal(percentile([10, 20, 30, 40], 0.95), 38.5);
});

test('summary exposes frame and FPS values', () => {
  const report = summarizeFrames([10, 10, 20, 20]);
  assert.equal(report.frames, 4);
  assert.equal(report.meanFrameMs, 15);
  assert.equal(report.p95FrameMs, 20);
  assert.equal(report.meanFps, 1000 / 15);
});
```

- [ ] **Step 2: Confirm the tests fail**

Run: `node --test web/benchmark/test/metrics.test.mjs`
Expected: FAIL because the metrics module does not exist.

- [ ] **Step 3: Implement pure summaries and browser collection**

```js
export function percentile(values, q) { /* sorted linear interpolation */ }

export function summarizeFrames(frameMs) {
  // Return frames, meanFrameMs, p50FrameMs, p95FrameMs,
  // p99FrameMs and meanFps.
}

export function createBenchmarkCollector({ warmupMs = 1500, sampleMs = 8000 } = {}) {
  // Sample requestAnimationFrame after warmup.
  // Observe supported 'longtask' entries.
  // finish(renderer) returns JSON-safe timings, long tasks,
  // viewport/DPR and renderer.info counters.
}
```

- [ ] **Step 4: Verify and commit**

Run: `node --test web/benchmark/test/metrics.test.mjs`
Expected: two PASS results.

```bash
git add web/benchmark/lib/metrics.mjs web/benchmark/test/metrics.test.mjs
git commit -m "feat: add KG benchmark frame metrics"
```

### Task 3: Interactive baseline runner

**Files:**
- Create: `web/benchmark/lib/benchmark-scene.mjs`
- Create: `web/benchmark/index.html`

- [ ] **Step 1: Build the runner interface**

Create controls for fixture profile, DPR (`1`, `2`, `native`) and five scenarios: `idle`, `orbit`, `focus`, `drag-edge-refresh`, `ui-reserve`. Include `#stage` and an `aria-live="polite"` `#report`. Use the same Three.js 0.160 import map as the showcase page.

- [ ] **Step 2: Implement a disposable scene contract**

```js
export function createBenchmarkScene({ container, fixture, quality, labelMode }) {
  // Create renderer, scene, camera, controls, node group and edge group.
  // Return { startScenario, stop, dispose, getRendererStats }.
}
```

For `quality === 'hero'`, mirror the existing cost model: one shader glass mesh for every visible node, two edge representations for every visible edge and floating CSS2D labels. `dispose()` must cancel animation frames, dispose every material/geometry and remove both renderer and label DOM roots.

- [ ] **Step 3: Implement deterministic scenarios**

```js
scene.startScenario('idle');
scene.startScenario('orbit');
scene.startScenario('focus');
scene.startScenario('drag-edge-refresh');
scene.startScenario('ui-reserve');
```

`focus` runs a deterministic BFS target animation. `drag-edge-refresh` moves one known node and refreshes only incident edges. `ui-reserve` adds a fixed CSS side-panel skeleton and transform animation, but does not import the deep-space background.

- [ ] **Step 4: Add result classification**

```js
function classify(report) {
  if (report.p95FrameMs <= 10 && report.p99FrameMs <= 20) return 'pass';
  if (report.p95FrameMs <= 16.7 && report.p99FrameMs <= 25) return 'reserve-warning';
  return 'fail';
}
```

Display profile, scenario, viewport, DPR, first-render time, P50/P95/P99, mean FPS, draw calls, geometry count, long-task count and classification. Add a copy action using `navigator.clipboard.writeText(JSON.stringify(report, null, 2))`.

- [ ] **Step 5: Verify in browser and commit**

```bash
python -m http.server 52700 --directory E:\\test\\kg-demo
npx --yes --package @playwright/cli playwright-cli --session kg-bench open http://127.0.0.1:52700/web/benchmark/
npx --yes --package @playwright/cli playwright-cli --session kg-bench snapshot
```

Expected: the page exposes five scenario controls, defaults to `legacy`, and displays a JSON-safe report after an idle run.

```bash
git add web/benchmark/index.html web/benchmark/lib/benchmark-scene.mjs
git commit -m "feat: add interactive KG performance benchmark"
```

### Task 4: Regression protection and measured baseline

**Files:**
- Create: `docs/PERFORMANCE_RESULTS.md`
- Verify: `web/index3d-bounce.html`

- [ ] **Step 1: Capture showcase invariants before optimization**

At 1440×960 and 1920×1080, capture overview and focused-node screenshots. Verify:

```text
- Labels remain independent CSS2D objects above nodes.
- Focus relayout moves labels with nodes; labels are not pinned to a grid.
- Hover emphasizes direct relations only.
- A drag does not accidentally trigger focus.
- Releasing a drag starts the existing spring-back behavior.
```

- [ ] **Step 2: Run and record only actual measurements**

Run `legacy` at DPR 1 and 2 for all five scenarios. Run `localDense` at DPR 1 for `idle`, `orbit`, `focus` and `drag-edge-refresh`. Never run `stressAggregate` in `hero` mode; document it as an invalid rendering strategy rather than a showcase failure.

Create this result table and enter only values emitted by the runner:

```markdown
| Date | Profile | Scenario | Viewport | DPR | First render (ms) | P95 (ms) | P99 (ms) | Mean FPS | Draw calls | Long tasks | Classification |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
```

- [ ] **Step 3: Run final verification and commit**

```bash
node --test web/benchmark/test/graph-fixtures.test.mjs web/benchmark/test/metrics.test.mjs
git add docs/PERFORMANCE_RESULTS.md
git commit -m "docs: record initial KG benchmark results"
```

Expected: all Node tests pass and the showcase retains the five visual/interaction invariants.

## Self-review

- This plan measures KG independently, maintains a 40% frame-budget reserve and defers deep-space fusion.
- It makes no production visual change to `web/index3d-bounce.html`; dynamic, floating labels are explicit protected behavior.
- It creates evidence before selecting instancing, aggregation or label-LOD optimizations.
- The defined profile names are consistent across fixtures, runner and result documentation.
