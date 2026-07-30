export function percentile(values, q) {
  if (!values.length) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  const position = (sorted.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower];
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

export function summarizeFrames(frameMs) {
  const frames = frameMs.length;
  const meanFrameMs = frames
    ? frameMs.reduce((sum, value) => sum + value, 0) / frames
    : 0;

  return {
    frames,
    meanFrameMs,
    p50FrameMs: percentile(frameMs, 0.5),
    p95FrameMs: percentile(frameMs, 0.95),
    p99FrameMs: percentile(frameMs, 0.99),
    meanFps: meanFrameMs ? 1000 / meanFrameMs : 0,
  };
}

export function firstRenderDuration(createdAt, renderedAt) {
  return Math.max(0, renderedAt - createdAt);
}

export function createBenchmarkCollector({ warmupMs = 1500, sampleMs = 8000 } = {}) {
  const frameMs = [];
  const longTasks = [];
  const startedAt = performance.now();
  let previousFrameAt = null;
  let sampleStartedAt = null;
  let animationFrameId = null;
  let observer = null;

  if (typeof PerformanceObserver !== 'undefined') {
    observer = new PerformanceObserver((entries) => {
      entries.getEntries().forEach((entry) => longTasks.push(entry.duration));
    });
    try {
      // Historical entries belong to earlier benchmark runs. Each collector must
      // only report long tasks that occur after it is created.
      observer.observe({ type: 'longtask' });
    } catch {
      observer.disconnect();
      observer = null;
    }
  }

  function tick(now) {
    if (sampleStartedAt === null && now - startedAt >= warmupMs) {
      sampleStartedAt = now;
      previousFrameAt = now;
    } else if (sampleStartedAt !== null && previousFrameAt !== null) {
      frameMs.push(now - previousFrameAt);
      previousFrameAt = now;
    }
    animationFrameId = requestAnimationFrame(tick);
  }

  return {
    start() {
      if (animationFrameId === null) animationFrameId = requestAnimationFrame(tick);
    },
    isComplete(now = performance.now()) {
      return sampleStartedAt !== null && now - sampleStartedAt >= sampleMs;
    },
    finish(renderer, firstRenderMs = 0) {
      if (animationFrameId !== null) cancelAnimationFrame(animationFrameId);
      observer?.disconnect();
      animationFrameId = null;
      return {
        ...summarizeFrames(frameMs),
        firstRenderMs,
        longTaskCount: longTasks.length,
        longTaskMs: longTasks.reduce((sum, value) => sum + value, 0),
        viewport: { width: window.innerWidth, height: window.innerHeight },
        devicePixelRatio: renderer.getPixelRatio(),
        drawCalls: renderer.info.render.calls,
        geometries: renderer.info.memory.geometries,
        textures: renderer.info.memory.textures,
      };
    },
  };
}
