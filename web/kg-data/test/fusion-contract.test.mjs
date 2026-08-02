import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

test('exploration composition keeps a passive background behind a transparent KG layer', async () => {
  const page = await readFile(new URL('../../exploration.html', import.meta.url), 'utf8');

  assert.match(page, /deep-space-galaxy\.html\?passive=1/);
  assert.match(page, /index3d-bounce\.html\?transparentBackground=1/);
  assert.match(page, /\.background-layer\s*\{[^}]*pointer-events:\s*none/s);
  assert.match(page, /\.show-guides::before/);
});

test('exploration forwards an explicit benchmark profile to the KG layer', async () => {
  const page = await readFile(new URL('../../exploration.html', import.meta.url), 'utf8');

  assert.match(page, /params\.get\('benchmark'\)/);
  assert.match(page, /transparentBackground=1&benchmark=/);
});
