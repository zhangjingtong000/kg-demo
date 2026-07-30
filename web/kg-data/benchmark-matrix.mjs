const SCALE_PROFILES = ['S0', 'S1', 'S2', 'S3', 'S4'];
const HERO_PROFILES = ['S0', 'S2'];

function appendRuns(matrix, { profiles, scenarios, dpr }) {
  for (const profile of profiles) {
    for (const scenario of scenarios) {
      for (let iteration = 0; iteration < 6; iteration += 1) {
        matrix.push({
          profile,
          scenario,
          dpr,
          iteration: iteration + 1,
          warmup: iteration === 0,
        });
      }
    }
  }
}

export function createBenchmarkMatrix() {
  const matrix = [];

  // Find the high-fidelity scale boundary on one stable rendering baseline.
  appendRuns(matrix, { profiles: SCALE_PROFILES, scenarios: ['idle', 'focus', 'drag-return'], dpr: 1 });

  // Verify the complete showcase interaction set at both hero-relevant sizes.
  appendRuns(matrix, { profiles: HERO_PROFILES, scenarios: ['idle', 'orbit', 'focus', 'drag-return'], dpr: 2 });

  // Measure UI reservation separately; it is intentionally excluded from S3/S4.
  appendRuns(matrix, { profiles: HERO_PROFILES, scenarios: ['ui-reserve'], dpr: 1 });
  appendRuns(matrix, { profiles: HERO_PROFILES, scenarios: ['ui-reserve'], dpr: 2 });

  return matrix;
}
