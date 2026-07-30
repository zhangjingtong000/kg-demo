import assert from 'node:assert/strict';
import test from 'node:test';
import {
  GRAPH_PROFILE_COUNTS,
  createGraphProfile,
  createSeededRandom,
  selectGraphProfile,
} from '../graph-profiles.mjs';

test('S0 is the exact current showcase graph size', () => {
  const graph = createGraphProfile('S0', 20260730);

  assert.equal(graph.nodes.length, 26);
  assert.equal(graph.edges.length, 65);
  assert.equal(graph.nodes[0].label, 'Deadlift');
  assert.deepEqual(graph.edges.slice(0, 4), [[0, 1], [0, 9], [0, 10], [0, 14]]);
});

test('every fixed benchmark profile has its documented number of nodes and edges', () => {
  for (const [name, counts] of Object.entries(GRAPH_PROFILE_COUNTS)) {
    const graph = createGraphProfile(name, 20260730);
    assert.equal(graph.nodes.length, counts.nodes, name);
    assert.equal(graph.edges.length, counts.edges, name);
  }
});

test('generated profiles are deterministic and all relations have valid distinct endpoints', () => {
  const first = createGraphProfile('S3', 20260730);
  const second = createGraphProfile('S3', 20260730);

  assert.deepEqual(first, second);
  for (const [from, to] of first.edges) {
    assert.ok(Number.isInteger(from) && from >= 0 && from < first.nodes.length);
    assert.ok(Number.isInteger(to) && to >= 0 && to < first.nodes.length);
    assert.notEqual(from, to);
  }
});

test('benchmark URL selection keeps the showcase as S0 and makes seeded profiles explicit', () => {
  assert.deepEqual(selectGraphProfile(''), { profile: 'S0', seed: 20260730, benchmark: false });
  assert.deepEqual(selectGraphProfile('?benchmark=S2&seed=7'), { profile: 'S2', seed: 7, benchmark: true });
});

test('benchmark layout randomness is repeatable for the same seed', () => {
  const left = createSeededRandom(7);
  const right = createSeededRandom(7);

  assert.deepEqual(
    Array.from({ length: 5 }, () => left()),
    Array.from({ length: 5 }, () => right()),
  );
});
