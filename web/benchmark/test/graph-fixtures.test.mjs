import test from 'node:test';
import assert from 'node:assert/strict';
import { createFixture, FIXTURE_PROFILES } from '../lib/graph-fixtures.mjs';

test('fixtures are deterministic for the same profile and seed', () => {
  assert.deepEqual(createFixture('localDense', 42), createFixture('localDense', 42));
});

test('every edge has two valid, distinct endpoints', () => {
  const fixture = createFixture('communityBrowse', 42);
  const ids = new Set(fixture.nodes.map((node) => node.id));

  for (const edge of fixture.edges) {
    assert.ok(ids.has(edge.source));
    assert.ok(ids.has(edge.target));
    assert.notEqual(edge.source, edge.target);
  }
});

test('fixture profiles expose the documented node and edge counts', () => {
  for (const [name, profile] of Object.entries(FIXTURE_PROFILES)) {
    const fixture = createFixture(name, 42);
    assert.equal(fixture.nodes.length, profile.nodes);
    assert.equal(fixture.edges.length, profile.edges);
  }
});
