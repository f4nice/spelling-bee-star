import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { prepareRequest, callGrok } from '../scripts/grok-dev.mjs';

function fixture(t) {
  const directory = mkdtempSync(path.join(os.tmpdir(), 'speakeasy-grok-test-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const root = path.join(directory, 'repo');
  mkdirSync(root);
  writeFileSync(path.join(root, 'sample.js'), 'const a = 1;\nconst b = 2;\nconst c = 3;');
  return { root, directory };
}

test('sends only requested lines with bounded output and no tools or response storage', (t) => {
  const { root } = fixture(t);
  const { body, summary } = prepareRequest({ task: 'Review b.', files: [{ path: 'sample.js', start: 2, end: 2 }] }, root);
  const content = JSON.parse(body.input);
  assert.equal(content.source_excerpts[0].text, '2: const b = 2;');
  assert.equal(body.max_output_tokens, 2048);
  assert.equal(body.reasoning.effort, 'low');
  assert.equal(body.store, false);
  assert.deepEqual(body.tools, []);
  assert.equal(summary.files[0].text, undefined);
});

test('rejects escape paths, hidden credentials, runtime data, and embedded secrets', (t) => {
  const { root, directory } = fixture(t);
  writeFileSync(path.join(directory, 'outside.js'), 'outside');
  writeFileSync(path.join(root, '.env'), 'private');
  mkdirSync(path.join(root, 'uploads'));
  writeFileSync(path.join(root, 'uploads', 'private.json'), '{}');
  writeFileSync(path.join(root, 'secret.js'), 'const api_key = "example-secret-value-123456";');
  for (const file of ['../outside.js', '.env', 'uploads/private.json', 'secret.js']) {
    assert.throws(() => prepareRequest({ task: 'Review.', files: [{ path: file }] }, root));
  }
  assert.throws(() => prepareRequest({ task: `Review xai-${'a'.repeat(30)}` }, root), /credential/);
});

test('rejects excessive context, invalid line ranges, and excessive output budgets', (t) => {
  const { root } = fixture(t);
  writeFileSync(path.join(root, 'large.js'), 'word '.repeat(15000));
  assert.throws(() => prepareRequest({ task: 'Review.', files: [{ path: 'large.js' }] }, root), /60000/);
  assert.throws(() => prepareRequest({ task: 'Review.', files: [{ path: 'sample.js', end: 4 }] }, root), /line range/);
  assert.throws(() => prepareRequest({ task: 'Review.', maxOutputTokens: 10000 }, root), /4096/);
  assert.throws(() => prepareRequest({ task: 'Review.', files: Array(7).fill({ path: 'sample.js' }) }, root), /6/);
});

test('never sends a request without credentials', async () => {
  let calls = 0;
  await assert.rejects(callGrok({}, { apiKey: '', fetchImpl: () => { calls++; } }), /missing/);
  assert.equal(calls, 0);
});

test('single official request, no redirects, compact usage, and response key redaction', async () => {
  let calls = 0;
  const key = 'test-key-never-print';
  const result = await callGrok({ input: 'Review.' }, {
    apiKey: key,
    fetchImpl: async (url, options) => {
      calls++;
      assert.equal(url, 'https://api.x.ai/v1/responses');
      assert.equal(options.redirect, 'error');
      assert.equal(options.headers.Authorization, `Bearer ${key}`);
      return { ok: true, json: async () => ({
        status: 'completed',
        output: [
          { type: 'reasoning', encrypted_content: 'do not save' },
          { type: 'message', content: [{ type: 'output_text', text: `Finding ${key}` }] },
        ],
        usage: { input_tokens: 100, output_tokens: 10, total_tokens: 110, unknown: 'do not save' },
      }) };
    },
  });
  assert.equal(calls, 1);
  assert.equal(result.text, 'Finding [REDACTED]');
  assert.deepEqual(result.usage, { input_tokens: 100, output_tokens: 10, total_tokens: 110 });
});

test('HTTP and network failures do not expose secrets or retry', async () => {
  for (const failure of ['http', 'network']) {
    let calls = 0;
    await assert.rejects(callGrok({}, {
      apiKey: 'test-key',
      fetchImpl: async () => {
        calls++;
        if (failure === 'network') throw new Error('test-key');
        return { ok: false, status: 429, json: async () => ({ error: 'test-key' }) };
      },
    }), (error) => !error.message.includes('test-key') && /retry/i.test(error.message));
    assert.equal(calls, 1);
  }
});

test('incomplete results are visibly marked and are not retried', async () => {
  const result = await callGrok({}, { apiKey: 'test-key', fetchImpl: async () => ({ ok: true, json: async () => ({
    status: 'incomplete', output: [{ type: 'message', content: [{ type: 'output_text', text: 'Partial proposal' }] }],
  }) }) });
  assert.equal(result.status, 'incomplete');
});
