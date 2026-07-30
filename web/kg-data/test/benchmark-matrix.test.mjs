import assert from 'node:assert/strict';
import test from 'node:test';
import { createBenchmarkMatrix } from '../benchmark-matrix.mjs';

test('matrix keeps a warmup plus five recorded runs for every selected case', () => {
  const matrix = createBenchmarkMatrix();
  const s0Idle = matrix.filter((run) => run.profile === 'S0' && run.scenario === 'idle' && run.dpr === 1);

  assert.equal(s0Idle.length, 6);
  assert.equal(s0Idle.filter((run) => run.warmup).length, 1);
  assert.equal(s0Idle.filter((run) => !run.warmup).length, 5);
});

test('matrix separates scale, high-DPR and UI-reserve measurements', () => {
  const matrix = createBenchmarkMatrix();

  assert.ok(matrix.some((run) => run.profile === 'S4' && run.scenario === 'focus' && run.dpr === 1));
  assert.ok(matrix.some((run) => run.profile === 'S2' && run.scenario === 'orbit' && run.dpr === 2));
  assert.ok(matrix.some((run) => run.profile === 'S0' && run.scenario === 'ui-reserve' && run.dpr === 1));
  assert.ok(!matrix.some((run) => run.profile === 'S4' && run.scenario === 'ui-reserve'));
});
