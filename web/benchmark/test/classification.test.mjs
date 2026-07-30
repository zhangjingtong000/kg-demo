import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyReport } from '../lib/classification.mjs';

test('classifies reports that retain the independent KG budget as pass', () => {
  assert.equal(classifyReport({ p95FrameMs: 10, p99FrameMs: 20 }), 'pass');
});

test('classifies reports within the final budget as reserve warning', () => {
  assert.equal(classifyReport({ p95FrameMs: 16.7, p99FrameMs: 25 }), 'reserve-warning');
});

test('classifies reports over the final budget as fail', () => {
  assert.equal(classifyReport({ p95FrameMs: 16.8, p99FrameMs: 25 }), 'fail');
});
