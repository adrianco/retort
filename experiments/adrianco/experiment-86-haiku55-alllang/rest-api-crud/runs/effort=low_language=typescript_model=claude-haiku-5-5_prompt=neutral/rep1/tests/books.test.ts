import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import type { AddressInfo } from 'node:net';
import { BookRepository } from '../src/repository';
import { createServer } from '../src/app';
import { validateBookInput } from '../src/book';

interface Response { status: number; body: any }

function request(port: number, method: string, path: string, body?: unknown, raw?: string): Promise<Response> {
  return new Promise((resolve, reject) => {
    const payload = raw ?? (body === undefined ? undefined : JSON.stringify(body));
    const req = http.request(
      { host: '127.0.0.1', port, method, path, headers: payload ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } : {} },
      (res) => {
        const chunks: Buffer[] = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const text = Buffer.concat(chunks).toString('utf8');
          resolve({ status: res.statusCode ?? 0, body: text ? JSON.parse(text) : undefined });
        });
      },
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

const valid = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' };

describe('validateBookInput', () => {
  test('requires title and author on create', () => {
    const result = validateBookInput({ year: 2000 });
    assert.equal(result.ok, false);
    if (!result.ok) assert.deepEqual(Object.keys(result.errors).sort(), ['author', 'title']);
  });

  test('rejects non-object bodies', () => {
    assert.equal(validateBookInput('nope').ok, false);
    assert.equal(validateBookInput([]).ok, false);
  });

  test('allows partial updates without title/author', () => {
    assert.deepEqual(validateBookInput({ year: 1999 }, true), { ok: true, value: { year: 1999 } });
  });

  test('rejects blank titles and non-integer years', () => {
    const result = validateBookInput({ title: '   ', author: 'A', year: 1.5 });
    assert.equal(result.ok, false);
    if (!result.ok) assert.deepEqual(Object.keys(result.errors).sort(), ['title', 'year']);
  });
});

describe('Book API', () => {
  let repo: BookRepository;
  let server: http.Server;
  let port: number;

  before(async () => {
    repo = new BookRepository(':memory:');
    server = createServer(repo);
    await new Promise<void>((r) => server.listen(0, '127.0.0.1', r));
    port = (server.address() as AddressInfo).port;
  });

  after(async () => {
    await new Promise<void>((r) => server.close(() => r()));
    repo.close();
  });

  test('GET /health reports ok', async () => {
    const res = await request(port, 'GET', '/health');
    assert.equal(res.status, 200);
    assert.deepEqual(res.body, { status: 'ok' });
  });

  test('full CRUD lifecycle', async () => {
    const created = await request(port, 'POST', '/books', valid);
    assert.equal(created.status, 201);
    assert.equal(created.body.title, 'Dune');
    const id = created.body.id;

    const fetched = await request(port, 'GET', `/books/${id}`);
    assert.equal(fetched.status, 200);
    assert.deepEqual(fetched.body, created.body);

    const updated = await request(port, 'PUT', `/books/${id}`, { year: 1966 });
    assert.equal(updated.status, 200);
    assert.equal(updated.body.year, 1966);
    assert.equal(updated.body.title, 'Dune');

    const deleted = await request(port, 'DELETE', `/books/${id}`);
    assert.equal(deleted.status, 204);

    assert.equal((await request(port, 'GET', `/books/${id}`)).status, 404);
  });

  test('POST rejects invalid input with 400 and details', async () => {
    const res = await request(port, 'POST', '/books', { year: 'x' });
    assert.equal(res.status, 400);
    assert.ok(res.body.details.title);
    assert.ok(res.body.details.author);
    assert.ok(res.body.details.year);
  });

  test('POST rejects malformed JSON', async () => {
    const res = await request(port, 'POST', '/books', undefined, '{not json');
    assert.equal(res.status, 400);
  });

  test('GET /books filters by author', async () => {
    await request(port, 'POST', '/books', { title: 'Emma', author: 'Jane Austen', year: 1815 });
    await request(port, 'POST', '/books', { title: 'Persuasion', author: 'Jane Austen', year: 1817 });
    const res = await request(port, 'GET', '/books?author=Jane%20Austen');
    assert.equal(res.status, 200);
    assert.ok(res.body.length >= 2);
    assert.ok(res.body.every((b: any) => b.author === 'Jane Austen'));
  });

  test('PUT on missing book returns 404; invalid id returns 400', async () => {
    assert.equal((await request(port, 'PUT', '/books/999999', { year: 2001 })).status, 404);
    assert.equal((await request(port, 'GET', '/books/abc')).status, 400);
  });

  test('PUT rejects blank title', async () => {
    const created = await request(port, 'POST', '/books', valid);
    const res = await request(port, 'PUT', `/books/${created.body.id}`, { title: '  ' });
    assert.equal(res.status, 400);
    assert.ok(res.body.details.title);
  });

  test('DELETE on missing book returns 404', async () => {
    assert.equal((await request(port, 'DELETE', '/books/999999')).status, 404);
  });

  test('unknown routes return 404 and wrong methods return 405', async () => {
    assert.equal((await request(port, 'GET', '/nope')).status, 404);
    assert.equal((await request(port, 'PATCH', '/books')).status, 405);
  });
});
