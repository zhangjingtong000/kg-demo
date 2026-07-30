import * as THREE from 'https://unpkg.com/three@0.160.0/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js';
import { CSS2DObject, CSS2DRenderer } from 'https://unpkg.com/three@0.160.0/examples/jsm/renderers/CSS2DRenderer.js';
import { firstRenderDuration } from './metrics.mjs';

const typeColors = { Concept: '#7dd3fc', Method: '#c4b5fd', Evidence: '#fde68a', Author: '#f9a8d4', Metric: '#86efac', Community: '#fdba74' };

export function createBenchmarkScene({ container, fixture, quality = 'hero', labelMode = 'all', pixelRatio = window.devicePixelRatio }) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#080c12');
  const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 300);
  camera.position.set(0, 18, 34);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(pixelRatio);
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);
  const labels = new CSS2DRenderer();
  labels.setSize(container.clientWidth, container.clientHeight);
  labels.domElement.className = 'benchmark-labels';
  container.appendChild(labels.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.autoRotate = false;
  scene.add(new THREE.AmbientLight('#9bb8d0', 1.4));
  const key = new THREE.DirectionalLight('#ffffff', 2.2); key.position.set(12, 18, 14); scene.add(key);
  const graph = new THREE.Group(); scene.add(graph);
  const meshes = new Map(); const incident = new Map(); const edgeObjects = [];
  const nodeGeometry = new THREE.SphereGeometry(0.42, 20, 16);
  fixture.nodes.forEach((node, index) => {
    const material = new THREE.MeshPhysicalMaterial({ color: typeColors[node.type], transmission: 0.25, transparent: true, opacity: 0.82, roughness: 0.22, metalness: 0.08, clearcoat: 0.6 });
    const mesh = new THREE.Mesh(nodeGeometry, material);
    mesh.position.set(node.x, node.y, node.z); mesh.userData.node = node; graph.add(mesh); meshes.set(node.id, mesh);
    if (labelMode === 'all' && (quality === 'hero' || index < 80)) {
      const el = document.createElement('div'); el.className = 'node-label'; el.textContent = node.label;
      const label = new CSS2DObject(el); label.position.set(0, 0.62, 0); mesh.add(label);
    }
  });
  fixture.edges.forEach((edge) => {
    const source = meshes.get(edge.source); const target = meshes.get(edge.target);
    const main = makeEdge(source.position, target.position, 0.028, 0.26);
    const core = makeEdge(source.position, target.position, 0.012, 0.62);
    graph.add(main, core); edgeObjects.push({ edge, main, core, source, target });
    [edge.source, edge.target].forEach((id) => incident.set(id, [...(incident.get(id) ?? []), edgeObjects.at(-1)]));
  });
  let raf = 0; let scenario = 'idle'; let focusProgress = 0; let firstRenderAt = null; const createdAt = performance.now();
  function makeEdge(a, b, radius, opacity) {
    const curve = new THREE.LineCurve3(a.clone(), b.clone());
    const geometry = new THREE.TubeGeometry(curve, 12, radius, 4, false);
    return new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color: '#dbeafe', transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false }));
  }
  function refreshEdge(item) {
    [item.main, item.core].forEach((mesh, index) => { mesh.geometry.dispose(); mesh.geometry = new THREE.TubeGeometry(new THREE.LineCurve3(item.source.position.clone(), item.target.position.clone()), 12, index ? 0.012 : 0.028, 4, false); });
  }
  function render(now) {
    if (firstRenderAt === null) firstRenderAt = firstRenderDuration(createdAt, performance.now());
    if (scenario === 'orbit') graph.rotation.y += 0.003;
    if (scenario === 'focus') { focusProgress = Math.min(1, focusProgress + 0.012); graph.scale.setScalar(1 + focusProgress * 0.12); }
    if (scenario === 'drag-edge-refresh') { const mesh = meshes.get(fixture.nodes[0].id); mesh.position.x += Math.sin(now * 0.003) * 0.008; (incident.get(fixture.nodes[0].id) ?? []).forEach(refreshEdge); }
    controls.update(); renderer.render(scene, camera); labels.render(scene, camera); raf = requestAnimationFrame(render);
  }
  raf = requestAnimationFrame(render);
  return { startScenario(name) { scenario = name; focusProgress = 0; }, stop() { cancelAnimationFrame(raf); }, dispose() { cancelAnimationFrame(raf); controls.dispose(); edgeObjects.forEach(({ main, core }) => [main, core].forEach((mesh) => { mesh.geometry.dispose(); mesh.material.dispose(); })); meshes.forEach((mesh) => mesh.material.dispose()); nodeGeometry.dispose(); renderer.dispose(); renderer.domElement.remove(); labels.domElement.remove(); }, getRendererStats() { return { renderer, firstRenderMs: firstRenderAt ?? 0 }; } };
}
