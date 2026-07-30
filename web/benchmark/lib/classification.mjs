export function classifyReport({ p95FrameMs, p99FrameMs }) {
  if (p95FrameMs <= 10 && p99FrameMs <= 20) return 'pass';
  if (p95FrameMs <= 16.7 && p99FrameMs <= 25) return 'reserve-warning';
  return 'fail';
}
