// frontend/src/public-help/publicHelpNoNetwork.test.js
//
// The public help tier must make no network call of any kind, so /help works
// while the backend is completely down (see the header comment in
// PublicHelpPage.jsx). That invariant was previously enforced only by a code
// comment. This test pins it from source: nothing under this directory may
// import from api/, from the polling hook useHelpManifest.js, or reference
// `fetch` at all -- and the lockout copy the invariant exists to protect
// must actually be present on the page.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.dirname(fileURLToPath(import.meta.url));

function sourceFiles() {
  return fs.readdirSync(DIR)
    .filter((name) => /\.(js|jsx)$/.test(name) && !name.endsWith('.test.js'))
    .map((name) => path.join(DIR, name));
}

test('public-help source files exist to scan (this test is not vacuously passing)', () => {
  assert.ok(sourceFiles().length > 0);
});

test('no file under public-help/ imports from api/', () => {
  for (const file of sourceFiles()) {
    const text = fs.readFileSync(file, 'utf8');
    assert.doesNotMatch(
      text,
      /from\s+['"][^'"]*\/api\//,
      `${path.basename(file)} must not import from an api/ module`,
    );
  }
});

test('no file under public-help/ imports useHelpManifest.js (the polling hook)', () => {
  for (const file of sourceFiles()) {
    const text = fs.readFileSync(file, 'utf8');
    assert.doesNotMatch(
      text,
      /from\s+['"][^'"]*useHelpManifest/,
      `${path.basename(file)} must not import useHelpManifest (network-backed manifest hook)`,
    );
  }
});

test('no file under public-help/ references fetch', () => {
  for (const file of sourceFiles()) {
    const text = fs.readFileSync(file, 'utf8');
    assert.doesNotMatch(
      text,
      /\bfetch\s*\(/,
      `${path.basename(file)} must not call fetch -- the public tier must work with the backend down`,
    );
  }
});

test('no file under public-help/ imports XMLHttpRequest, axios, or WebSocket', () => {
  for (const file of sourceFiles()) {
    const text = fs.readFileSync(file, 'utf8');
    assert.doesNotMatch(text, /XMLHttpRequest|axios|WebSocket/, `${path.basename(file)} must not reach the network`);
  }
});

test('the public page renders the admin-access lockout copy', () => {
  const pageFile = path.join(DIR, 'PublicHelpPage.jsx');
  const text = fs.readFileSync(pageFile, 'utf8');
  assert.match(
    text,
    /Stjórnandaaðgangur er ekki tiltækur\. Hafðu samband við kerfisstjóra\./,
    'the public tier lockout string must be present as fixed page chrome',
  );
});
