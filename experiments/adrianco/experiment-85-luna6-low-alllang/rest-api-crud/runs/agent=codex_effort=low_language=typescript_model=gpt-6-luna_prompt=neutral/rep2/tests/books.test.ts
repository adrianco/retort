import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Readable } from 'node:stream';
import { DatabaseSync } from 'node:sqlite';
import { handleRequest } from '../src/app.ts';
import type { IncomingMessage, ServerResponse } from 'node:http';

async function call(db: DatabaseSync, url: string, method = 'GET', body?: unknown) {
  const raw = body === undefined ? '' : JSON.stringify(body);
  const req = Readable.from(raw ? [raw] : []) as IncomingMessage;
  req.method = method;
  req.url = url;
  let status = 200;
  let responseBody = '';
  const res = {
    writeHead(code: number) { status = code; return this; },
    end(value?: string) { responseBody = value ?? ''; return this; },
  } as unknown as ServerResponse;
  await handleRequest(db, req, res);
  return { status, body: responseBody ? JSON.parse(responseBody) : undefined };
}

function freshDb(): DatabaseSync {
  const db = new DatabaseSync(':memory:');
  db.exec('CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)');
  return db;
}

test('health endpoint reports healthy', async () => {
  const db = freshDb();
  assert.deepEqual(await call(db, '/health'), { status: 200, body: { status: 'ok' } });
  db.close();
});

test('creates books and validates required title and author', async () => {
  const db = freshDb();
  assert.equal((await call(db, '/books', 'POST', { title: 'Untitled' })).status, 400);
  const created = await call(db, '/books', 'POST', {
    title: 'The Left Hand of Darkness', author: 'Ursula K. Le Guin', year: 1969, isbn: '9780441478125',
  });
  assert.equal(created.status, 201);
  assert.equal(created.body.id, 1);
  assert.equal(created.body.title, 'The Left Hand of Darkness');
  db.close();
});

test('lists books with an author filter and fetches one by ID', async () => {
  const db = freshDb();
  await call(db, '/books', 'POST', { title: 'A Wizard of Earthsea', author: 'Ursula K. Le Guin' });
  await call(db, '/books', 'POST', { title: 'Dune', author: 'Frank Herbert' });
  const filtered = await call(db, '/books?author=Le%20Guin');
  assert.equal(filtered.status, 200);
  assert.equal(filtered.body.length, 1);
  assert.equal((await call(db, '/books/1')).body.author, 'Ursula K. Le Guin');
  assert.equal((await call(db, '/books/999')).status, 404);
  db.close();
});

test('updates and deletes a book', async () => {
  const db = freshDb();
  const created = await call(db, '/books', 'POST', { title: 'Dune', author: 'Frank Herbert' });
  const id = created.body.id;
  const updated = await call(db, `/books/${id}`, 'PUT', { title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 });
  assert.equal(updated.status, 200);
  assert.equal(updated.body.title, 'Dune Messiah');
  assert.equal((await call(db, `/books/${id}`, 'DELETE')).status, 204);
  assert.equal((await call(db, `/books/${id}`)).status, 404);
  db.close();
});
