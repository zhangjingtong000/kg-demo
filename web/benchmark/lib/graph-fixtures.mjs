import { createSeededRng } from './seeded-rng.mjs';

export const FIXTURE_PROFILES = Object.freeze({
  legacy: { nodes: 26, edges: 55, communities: 4 },
  localDense: { nodes: 80, edges: 320, communities: 6 },
  communityBrowse: { nodes: 250, edges: 1200, communities: 12 },
  macroOverview: { nodes: 1000, edges: 5000, communities: 35 },
  stressAggregate: { nodes: 5000, edges: 20000, communities: 100 },
});

const ENTITY_TYPES = ['Concept', 'Method', 'Evidence', 'Author', 'Metric', 'Community'];
const RELATION_TYPES = ['RELATED_TO', 'SUPPORTS', 'USES', 'PART_OF'];

export function createFixture(profileName, seed = 20260730) {
  const profile = FIXTURE_PROFILES[profileName];
  if (!profile) throw new Error(`Unknown fixture profile: ${profileName}`);

  const rng = createSeededRng(seed);
  const nodes = Array.from({ length: profile.nodes }, (_, index) => createNode(index, profile, rng));
  const edges = createEdges(nodes, profile, rng);

  return { profileName, seed, nodes, edges };
}

function createNode(index, profile, rng) {
  const communityIndex = index % profile.communities;
  const communityAngle = (communityIndex / profile.communities) * Math.PI * 2;
  const communityRadius = 8 + (communityIndex % 5) * 2.2;
  const spread = 1.2 + rng.random() * 3.6;
  const type = rng.pick(ENTITY_TYPES);

  return {
    id: `n${index}`,
    label: `${type} ${index + 1}`,
    type,
    community: `c${communityIndex}`,
    x: Math.cos(communityAngle) * communityRadius + (rng.random() - 0.5) * spread,
    y: (rng.random() - 0.5) * 10,
    z: Math.sin(communityAngle) * communityRadius + (rng.random() - 0.5) * spread,
    importance: Number((0.2 + rng.random() * 0.8).toFixed(4)),
  };
}

function createEdges(nodes, profile, rng) {
  const edges = [];
  const keys = new Set();
  const addEdge = (source, target) => {
    if (source === target) return false;
    const key = source < target ? `${source}:${target}` : `${target}:${source}`;
    if (keys.has(key)) return false;
    keys.add(key);
    edges.push({
      id: `e${edges.length}`,
      source,
      target,
      type: rng.pick(RELATION_TYPES),
      weight: Number((0.25 + rng.random() * 0.75).toFixed(4)),
    });
    return true;
  };

  const membersByCommunity = new Map();
  for (const node of nodes) {
    const members = membersByCommunity.get(node.community) ?? [];
    members.push(node.id);
    membersByCommunity.set(node.community, members);
  }

  const communities = [...membersByCommunity.values()];
  for (const members of communities) {
    for (let index = 1; index < members.length; index += 1) addEdge(members[index - 1], members[index]);
  }
  for (let index = 1; index < communities.length; index += 1) addEdge(communities[index - 1][0], communities[index][0]);

  let attempts = 0;
  const maxAttempts = profile.edges * 50;
  while (edges.length < profile.edges && attempts < maxAttempts) {
    attempts += 1;
    const source = rng.pick(nodes);
    const preferLocal = rng.random() < 0.72;
    const candidates = preferLocal
      ? membersByCommunity.get(source.community)
      : nodes.map((node) => node.id);
    addEdge(source.id, rng.pick(candidates));
  }

  if (edges.length !== profile.edges) {
    throw new Error(`Could not create ${profile.edges} unique edges for ${profileName}`);
  }
  return edges;
}
