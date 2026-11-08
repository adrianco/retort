import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Readable, Writable } from 'node:stream';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { createApp } from '../app.js';

async function withServer(fn: (base: string) => Promise<void>) {
  const server = createApp(':memory:');
  activeServer = server;
  try { await fn('http://localhost'); }
  finally { server.emit('close'); }
}
let activeServer: ReturnType<typeof createApp>;
async function fetch(url: string, options: { method?: string; headers?: Record<string, string>; body?: string } = {}) {
  const request = Readable.from(options.body ? [options.body] : []) as IncomingMessage;
  request.url = new URL(url).pathname + new URL(url).search;
  request.method = options.method ?? 'GET';
  let status = 0;
  let content = '';
  const response = new Writable({ write(chunk, _encoding, callback) { content += chunk.toString(); callback(); } }) as ServerResponse;
  response.writeHead = ((code: number) => { status = code; return response; }) as typeof response.writeHead;
  const finished = new Promise<void>((resolve, reject) => { response.on('finish', resolve); response.on('error', reject); });
  activeServer.emit('request', request, response);
  await finished;
  return { status, json: async (): Promise<unknown> => JSON.parse(content) };
}
const json = (method: string, body: unknown) => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });

test('health and creation, retrieval, and author filtering', async () => withServer(async base => {
  assert.deepEqual(await (await fetch(`${base}/health`)).json(), { status: 'ok' });
  const response = await fetch(`${base}/books`, json('POST', { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '123' }));
  assert.equal(response.status, 201);
  const book = await response.json() as { id: number; title: string };
  assert.equal(book.title, 'Dune');
  await fetch(`${base}/books`, json('POST', { title: 'Other', author: 'Someone' }));
  assert.deepEqual(await (await fetch(`${base}/books/${book.id}`)).json(), book);
  assert.deepEqual(await (await fetch(`${base}/books?author=Frank%20Herbert`)).json(), [book]);
  assert.equal((await (await fetch(`${base}/books`)).json() as unknown[]).length, 2);
}));

test('validation rejects missing fields, malformed JSON and invalid optional fields', async () => withServer(async base => {
  for (const body of [{ author: 'A' }, { title: 'T', author: ' ' }, { title: 'T', author: 'A', year: 'x' }]) {
    assert.equal((await fetch(`${base}/books`, json('POST', body))).status, 400);
  }
  assert.equal((await fetch(`${base}/books`, { method: 'POST', body: '{' })).status, 400);
  assert.deepEqual(await (await fetch(`${base}/books`)).json(), []);
}));

test('update replaces fields and deletion makes book unavailable', async () => withServer(async base => {
  const created = await (await fetch(`${base}/books`, json('POST', { title: 'Old', author: 'A', year: 2000 }))).json() as { id: number };
  const url = `${base}/books/${created.id}`;
  const updated = await fetch(url, json('PUT', { title: 'New', author: 'B' }));
  assert.equal(updated.status, 200);
  assert.deepEqual(await updated.json(), { id: created.id, title: 'New', author: 'B', year: null, isbn: null });
  assert.equal((await fetch(url, { method: 'DELETE' })).status, 200);
  assert.equal((await fetch(url)).status, 404);
  assert.equal((await fetch(url, { method: 'DELETE' })).status, 404);
  assert.equal((await fetch(url, json('PUT', { title: 'X', author: 'Y' }))).status, 404);
}));
