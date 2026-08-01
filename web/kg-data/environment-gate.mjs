const MAX_CPU_DRIFT_PERCENT = 10;
const MAX_NON_TEST_GPU_DRIFT_PERCENT = 10;
const MAX_MEMORY_DROP_MB = 2000;

export function evaluateEnvironmentGate({ baseline, observed }) {
  const reasons = [];

  if (observed.cpuPercent - baseline.cpuPercent > MAX_CPU_DRIFT_PERCENT) {
    reasons.push('cpu-drift');
  }
  if (observed.nonTestGpuPercent - baseline.nonTestGpuPercent > MAX_NON_TEST_GPU_DRIFT_PERCENT) {
    reasons.push('non-test-gpu-drift');
  }
  if (baseline.availableMemoryMB - observed.availableMemoryMB > MAX_MEMORY_DROP_MB) {
    reasons.push('memory-drift');
  }

  return { accepted: reasons.length === 0, reasons };
}
