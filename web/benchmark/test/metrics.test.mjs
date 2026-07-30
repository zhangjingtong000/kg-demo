import test from 'node:test';
import assert from 'node:assert/strict';
import { percentile, summarizeFrames } from '../lib/metrics.mjs';

test('percentile uses sorted linear interpolation', () => {
  assert.equal(percentile([10, 20, 30, 40], 0.95), 38.5);
});

test('frame summaries include FPS and frame-time percentiles', () => {
  const report = summarizeFrames([10, 10, 20, 20]);
  assert.equal(report.frames, 4);
  assert.equal(report.meanFrameMs, 15);
  assert.equal(report.p95FrameMs, 20);
  assert.equal(report.meanFps, 1000 / 15);
});
