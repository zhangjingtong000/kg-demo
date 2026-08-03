# Semantic Filament Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an isolated, interactive 3 to 5 cloud prototype that validates aggregated cosmic-web-like links without changing the 80-node detail graph.

**Architecture:** A standalone Three.js page owns fixed prototype cloud and aggregated-link data. It renders cloud groups and cubic Bézier filament meshes locally, then derives hover emphasis and a single slow particle from the selected cloud. No backend request or shared detail-graph module is introduced.

**Tech Stack:** HTML, ES modules, Three.js CDN, OrbitControls, Playwright CLI for browser verification.

---

### Task 1: Create an isolated prototype page and deterministic cloud model

**Files:**
- Create: `web/prototype-semantic-filaments.html`
- Test: `output/playwright/semantic-filaments-initial.png`

- [ ] **Step 1: Define the five-cloud and six-aggregate-link model in the page module**

```js
const clouds = [
  { id: 'transformer', name: 'Transformer architecture', summary: 'Attention and encoder-decoder structure', position: [-8, 2, 0], size: 2.2, color: '#d7a7ff', entityCount: 36 },
  { id: 'attention', name: 'Attention mechanisms', summary: 'Multi-head attention and alignment', position: [-1, 4, -2], size: 2.8, color: '#7ecbff', entityCount: 52 },
  { id: 'translation', name: 'Machine translation', summary: 'Translation tasks and benchmarks', position: [8, 1, 1], size: 2.0, color: '#ffd27a', entityCount: 28 },
  { id: 'evaluation', name: 'Evaluation', summary: 'Metrics and comparison baselines', position: [5, -5, -1], size: 1.6, color: '#a7e3b5', entityCount: 18 },
  { id: 'sequence', name: 'Sequence modelling', summary: 'Recurrent and convolutional alternatives', position: [-7, -5, 2], size: 1.9, color: '#f3a6b9', entityCount: 31 }
];
const links = [
  { source: 'transformer', target: 'attention', strength: 'strong', relationCount: 19 },
  { source: 'attention', target: 'translation', strength: 'strong', relationCount: 15 },
  { source: 'attention', target: 'evaluation', strength: 'medium', relationCount: 8 },
  { source: 'transformer', target: 'sequence', strength: 'medium', relationCount: 7 },
  { source: 'sequence', target: 'evaluation', strength: 'weak', relationCount: 3 },
  { source: 'translation', target: 'evaluation', strength: 'weak', relationCount: 2 }
];
```

- [ ] **Step 2: Create the Three.js scene shell with a transparent canvas, orbit controls and a status label**

```js
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, innerWidth / innerHeight, 0.1, 1000);
camera.position.set(0, 2, 26);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setClearColor(0x000000, 0);
document.body.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
```

- [ ] **Step 3: Render each cloud as a labeled glowing group and expose its mesh for raycasting**

```js
function createCloud(cloud) {
  const group = new THREE.Group();
  const core = new THREE.Mesh(
    new THREE.SphereGeometry(cloud.size * 0.34, 32, 32),
    new THREE.MeshBasicMaterial({ color: cloud.color, transparent: true, opacity: 0.86 })
  );
  group.add(core);
  group.position.fromArray(cloud.position);
  core.userData.cloudId = cloud.id;
  return { cloud, group, core };
}
```

- [ ] **Step 4: Run the static server and capture the initial desktop screenshot**

Run: `npx --yes --package @playwright/cli playwright-cli open "http://127.0.0.1:52700/web/prototype-semantic-filaments.html" --headed`

Run: `npx --yes --package @playwright/cli playwright-cli screenshot --filename output/playwright/semantic-filaments-initial.png`

Expected: five labeled cloud groups on a transparent canvas, with no links yet.

- [ ] **Step 5: Commit the isolated shell**

```bash
git add web/prototype-semantic-filaments.html
git commit -m "feat: add semantic filament prototype shell"
```

### Task 2: Render aggregate relations as restrained curved filaments

**Files:**
- Modify: `web/prototype-semantic-filaments.html`
- Test: `output/playwright/semantic-filaments-links.png`

- [ ] **Step 1: Add a failing browser acceptance check by capturing the shell and confirming no aggregate relation is yet visible**

Run: `npx --yes --package @playwright/cli playwright-cli screenshot --filename output/playwright/semantic-filaments-before-links.png`

Expected: screenshot contains clouds but no curved filament meshes.

- [ ] **Step 2: Implement a curved filament factory that maps one aggregate link to two Bézier tubes**

```js
function createFilament(link, start, end) {
  const midpoint = start.clone().lerp(end, 0.5);
  const arc = new THREE.Vector3(-(end.y - start.y), end.x - start.x, 0).normalize();
  const control = midpoint.addScaledVector(arc, link.strength === 'strong' ? 2.2 : 1.2);
  control.z += link.strength === 'strong' ? 1.4 : 0.7;
  const curve = new THREE.QuadraticBezierCurve3(start, control, end);
  const profile = link.strength === 'strong'
    ? { radius: 0.052, opacity: 0.32, color: '#b9d6ff' }
    : { radius: 0.026, opacity: 0.18, color: '#829bc9' };
  const tube = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 48, profile.radius, 8, false),
    new THREE.MeshBasicMaterial({ color: profile.color, transparent: true, opacity: profile.opacity, depthWrite: false })
  );
  tube.userData = { link, curve, baseOpacity: profile.opacity };
  return tube;
}
```

- [ ] **Step 3: Hide weak filaments by default and make every cloud pair use at most one aggregate filament**

```js
const visibleByDefault = link => link.strength !== 'weak';
for (const link of links.filter(visibleByDefault)) {
  const start = cloudById.get(link.source).group.position;
  const end = cloudById.get(link.target).group.position;
  filamentObjects.push(createFilament(link, start, end));
}
```

- [ ] **Step 4: Capture and inspect the aggregate-link state**

Run: `npx --yes --package @playwright/cli playwright-cli screenshot --filename output/playwright/semantic-filaments-links.png`

Expected: strong links are visibly thicker than medium links, weak links are absent, and no star-cloud pair has multiple parallel visual links.

- [ ] **Step 5: Commit filament rendering**

```bash
git add web/prototype-semantic-filaments.html
git commit -m "feat: render aggregate semantic filaments"
```

### Task 3: Add cloud hover emphasis, weak-link reveal and a single low-speed particle

**Files:**
- Modify: `web/prototype-semantic-filaments.html`
- Test: `output/playwright/semantic-filaments-hover.png`

- [ ] **Step 1: Implement hover selection with a raycaster and one `activeCloudId` state**

```js
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let activeCloudId = null;
renderer.domElement.addEventListener('pointermove', event => {
  pointer.x = (event.clientX / innerWidth) * 2 - 1;
  pointer.y = -(event.clientY / innerHeight) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(cloudObjects.map(item => item.core), false)[0];
  activeCloudId = hit?.object.userData.cloudId ?? null;
});
```

- [ ] **Step 2: Reveal only the active cloud's weak links and dim unrelated filaments**

```js
function updateFilamentEmphasis() {
  filamentObjects.forEach(({ mesh, link }) => {
    const connected = activeCloudId && (link.source === activeCloudId || link.target === activeCloudId);
    mesh.visible = link.strength !== 'weak' || connected;
    mesh.material.opacity = !activeCloudId ? mesh.userData.baseOpacity : connected ? 0.62 : mesh.userData.baseOpacity * 0.24;
  });
}
```

- [ ] **Step 3: Add one particle per connected filament, updated from the stored Bézier curve**

```js
function updateParticle(particle, curve, elapsed) {
  particle.visible = Boolean(activeCloudId);
  particle.position.copy(curve.getPoint((elapsed * 0.035 + particle.userData.offset) % 1));
}
```

- [ ] **Step 4: Capture a hover state and inspect the page console**

Run: `npx --yes --package @playwright/cli playwright-cli snapshot`

Run: `npx --yes --package @playwright/cli playwright-cli screenshot --filename output/playwright/semantic-filaments-hover.png`

Run: `npx --yes --package @playwright/cli playwright-cli console error`

Expected: hovering a cloud highlights only its filaments, reveals its weak relationship and emits no application console errors.

- [ ] **Step 5: Commit interaction behavior**

```bash
git add web/prototype-semantic-filaments.html
git commit -m "feat: add semantic filament hover behavior"
```

### Task 4: Add detail-entry feedback and complete visual verification

**Files:**
- Modify: `web/prototype-semantic-filaments.html`
- Test: `output/playwright/semantic-filaments-entry.png`

- [ ] **Step 1: Add a click-only entry feedback without navigation**

```js
renderer.domElement.addEventListener('click', () => {
  if (!activeCloudId) return;
  const cloud = cloudById.get(activeCloudId).cloud;
  status.textContent = `进入「${cloud.name}」的局部知识图`;
  status.classList.add('visible');
});
```

- [ ] **Step 2: Verify the entry feedback, desktop rendering and compact rendering**

Run: `npx --yes --package @playwright/cli playwright-cli resize 1920 1080`

Run: `npx --yes --package @playwright/cli playwright-cli screenshot --filename output/playwright/semantic-filaments-entry.png`

Run: `npx --yes --package @playwright/cli playwright-cli resize 375 667`

Run: `npx --yes --package @playwright/cli playwright-cli screenshot --filename output/playwright/semantic-filaments-mobile.png`

Expected: the desktop view has no overflowing labels; compact view remains renderable and does not expose horizontal page scroll.

- [ ] **Step 3: Run the existing regression suite**

Run: `pytest -q`

Expected: `20 passed` or more, with no regression in the PDF and graph tests.

- [ ] **Step 4: Commit the completed prototype**

```bash
git add web/prototype-semantic-filaments.html
git commit -m "feat: complete semantic filament prototype"
```
