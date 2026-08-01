import assert from 'node:assert/strict';
import test from 'node:test';
import { evaluateEnvironmentGate } from '../environment-gate.mjs';

test('accepts a sample when system and non-test GPU load remain within the baseline band', () => {
  const result = evaluateEnvironmentGate({
    baseline: { cpuPercent: 28, availableMemoryMB: 16000, nonTestGpuPercent: 24 },
    observed: { cpuPercent: 31, availableMemoryMB: 15100, nonTestGpuPercent: 27 },
  });

  assert.deepEqual(result, { accepted: true, reasons: [] });
});

test('rejects a sample when outside workload rises beyond the fixed tolerance', () => {
  const result = evaluateEnvironmentGate({
    baseline: { cpuPercent: 28, availableMemoryMB: 16000, nonTestGpuPercent: 24 },
    observed: { cpuPercent: 46, availableMemoryMB: 14900, nonTestGpuPercent: 49 },
  });

  assert.equal(result.accepted, false);
  assert.deepEqual(result.reasons, ['cpu-drift', 'non-test-gpu-drift']);
});
