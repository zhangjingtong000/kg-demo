const SHOWCASE_NODES = Object.freeze([
  { pos: [-8, 6, -3], r: 0.60, color: '#e8c170', label: 'Deadlift' },
  { pos: [-5, 9, 2], r: 0.55, color: '#7db8d4', label: 'Hip Flexor' },
  { pos: [-1, 11, -4], r: 0.62, color: '#c9a0dc', label: 'Core Stability' },
  { pos: [4, 10, 1], r: 0.50, color: '#88c9a0', label: 'Shoulder Press' },
  { pos: [9, 7, 3], r: 0.64, color: '#e8a870', label: 'Bench Press' },
  { pos: [8, 2, -4], r: 0.56, color: '#d4a0b0', label: 'Triceps' },
  { pos: [5, -3, 5], r: 0.48, color: '#90b0d8', label: 'Biceps Curl' },
  { pos: [-1, -6, 1], r: 0.66, color: '#c0b890', label: 'Squat' },
  { pos: [-8, -2, 6], r: 0.58, color: '#a8c8b0', label: 'Quadriceps' },
  { pos: [-11, 2, -3], r: 0.52, color: '#d0b8c8', label: 'Lower Back' },
  { pos: [-4, -1, -8], r: 0.60, color: '#b8c0d8', label: 'Glutes' },
  { pos: [7, -6, -2], r: 0.54, color: '#c8b8a0', label: 'Hamstrings' },
  { pos: [-5, 4, 9], r: 0.50, color: '#a0c0c8', label: 'Lat Pulldown' },
  { pos: [3, 2, 10], r: 0.56, color: '#c8a8b8', label: 'Romanian DL' },
  { pos: [-9, -6, -5], r: 0.46, color: '#98b8c8', label: 'Calves' },
  { pos: [11, -2, 7], r: 0.58, color: '#e8d488', label: 'Overhead Press' },
  { pos: [-11, 8, 6], r: 0.52, color: '#c0a0e0', label: 'Pull-up' },
  { pos: [0, -10, -3], r: 0.62, color: '#d8c090', label: 'Leg Press' },
  { pos: [12, 1, -7], r: 0.54, color: '#e0a8b0', label: 'Chest Fly' },
  { pos: [-6, -9, 7], r: 0.50, color: '#b8d0c0', label: 'Lunges' },
  { pos: [8, 8, 8], r: 0.48, color: '#d0c8e8', label: 'Face Pull' },
  { pos: [-9, -1, 11], r: 0.56, color: '#e8c888', label: 'Hip Thrust' },
  { pos: [1, 7, -11], r: 0.54, color: '#c8b0d0', label: 'Plank' },
  { pos: [10, -9, 0], r: 0.54, color: '#a8d8c8', label: 'Calf Raise' },
  { pos: [-13, -4, 8], r: 0.48, color: '#d8b8a0', label: 'Good Morning' },
  { pos: [5, 5, -10], r: 0.54, color: '#b8a8d8', label: 'Russian Twist' },
]);

const SHOWCASE_EDGES = Object.freeze([
  [0,1],[0,9],[0,10],[0,14],[1,2],[2,3],[2,16],[3,4],[4,5],[4,20],
  [5,6],[6,7],[7,8],[7,17],[8,9],[10,7],[10,11],[11,23],[5,12],[6,12],
  [8,12],[11,14],[9,14],[3,13],[13,5],[12,21],[12,14],[1,8],[10,14],
  [15,4],[15,18],[15,5],[16,3],[16,20],[17,7],[17,11],[17,14],
  [8,19],[19,11],[19,14],[19,17],[0,25],[1,21],[2,22],[3,24],[4,23],
  [5,18],[6,20],[20,16],[21,13],[21,25],[22,16],[22,17],[7,23],[23,18],
  [23,10],[24,9],[24,8],[24,17],[25,12],[25,22],[25,0],[10,24],[11,19],[15,20],
]);

export const GRAPH_PROFILE_COUNTS = Object.freeze({
  S0: { nodes: 26, edges: 65, communities: 4 },
  S1: { nodes: 50, edges: 128, communities: 5 },
  S2: { nodes: 80, edges: 204, communities: 6 },
  S3: { nodes: 120, edges: 306, communities: 8 },
  S4: { nodes: 200, edges: 510, communities: 10 },
});

const COLORS = ['#e8c170', '#7db8d4', '#c9a0dc', '#88c9a0', '#e8a870', '#d4a0b0'];

export function createSeededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function copyGraph(nodes, edges, name) {
  return {
    profile: name,
    nodes: nodes.map((node) => ({ ...node, pos: [...node.pos] })),
    edges: edges.map(([from, to]) => [from, to]),
  };
}

function addEdge(edges, from, to) {
  if (from === to) return;
  const low = Math.min(from, to);
  const high = Math.max(from, to);
  edges.set(`${low}:${high}`, [low, high]);
}

function createGeneratedProfile(name, config, seed) {
  const random = createSeededRandom(seed);
  const nodes = [];
  const communityMembers = Array.from({ length: config.communities }, () => []);

  for (let index = 0; index < config.nodes; index += 1) {
    const community = index % config.communities;
    const angle = (community / config.communities) * Math.PI * 2;
    const radius = 9 + (random() - 0.5) * 5;
    const localAngle = random() * Math.PI * 2;
    communityMembers[community].push(index);
    nodes.push({
      pos: [
        Math.cos(angle) * 12 + Math.cos(localAngle) * radius * 0.7,
        (random() - 0.5) * 15,
        Math.sin(angle) * 12 + Math.sin(localAngle) * radius * 0.7,
      ],
      r: 0.46 + random() * 0.20,
      color: COLORS[community % COLORS.length],
      label: `${name} Entity ${String(index + 1).padStart(3, '0')}`,
    });
  }

  const edgeMap = new Map();
  communityMembers.forEach((members, community) => {
    members.forEach((node, index) => {
      addEdge(edgeMap, node, members[(index + 1) % members.length]);
      if (members.length > 2) addEdge(edgeMap, node, members[(index + 2) % members.length]);
    });
    addEdge(edgeMap, members[0], communityMembers[(community + 1) % config.communities][0]);
  });

  while (edgeMap.size < config.edges) {
    const from = Math.floor(random() * config.nodes);
    const local = random() < 0.72;
    const community = from % config.communities;
    const candidates = local ? communityMembers[community] : nodes.map((_, index) => index);
    const to = candidates[Math.floor(random() * candidates.length)];
    addEdge(edgeMap, from, to);
  }

  return { profile: name, nodes, edges: [...edgeMap.values()] };
}

export function createGraphProfile(name = 'S0', seed = 20260730) {
  if (name === 'S0') return copyGraph(SHOWCASE_NODES, SHOWCASE_EDGES, name);
  const config = GRAPH_PROFILE_COUNTS[name];
  if (!config) throw new Error(`Unknown graph profile: ${name}`);
  return createGeneratedProfile(name, config, seed);
}

export function selectGraphProfile(search = '') {
  const params = new URLSearchParams(search);
  const requested = params.get('benchmark');
  const seed = Number(params.get('seed') ?? 20260730);
  return {
    profile: requested || 'S0',
    seed: Number.isInteger(seed) ? seed : 20260730,
    benchmark: requested !== null,
  };
}
