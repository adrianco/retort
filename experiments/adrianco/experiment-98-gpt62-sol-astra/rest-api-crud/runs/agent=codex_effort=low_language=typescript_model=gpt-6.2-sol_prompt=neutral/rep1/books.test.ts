import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { Agent, request as httpRequest } from 'node:http';
import { Duplex } from 'node:stream';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test, type TestContext } from 'node:test';
import { createBookServer } from './books.js';

function start(t: TestContext, databasePath = ':memory:') {
  const server = createBookServer(databasePath);
  let closed = false;
  async function close() {
    if (closed) return;
    closed = true;
    // No listener was opened, but close still emits the event that releases SQLite.
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
  t.after(close);

  function request(path: string, init: RequestInit = {}) {
    return new Promise<Response>((resolve, reject) => {
      // Connect Node's real HTTP client and server without binding a socket.
      const agent = new Agent({ keepAlive: false });
      function endpoint(peer: () => Duplex) {
        return new Duplex({
          read() {},
          write(chunk: Buffer, _encoding, callback) {
            peer().push(chunk);
            callback();
          },
          final(callback) {
            peer().push(null);
            callback();
          },
        });
      }
      const clientSide: Duplex = endpoint(() => serverSide);
      const serverSide: Duplex = endpoint(() => clientSide);
      agent.createConnection = () => {
        server.emit('connection', serverSide);
        return clientSide;
      };

      const headers = Object.fromEntries(new Headers(init.headers));
      const body = typeof init.body === 'string' ? init.body : '';
      if (body) headers['content-length'] = String(Buffer.byteLength(body));
      const client = httpRequest({ path, method: init.method, headers, agent }, (incoming) => {
        const chunks: Buffer[] = [];
        incoming.on('data', (chunk: Buffer) => chunks.push(chunk));
        incoming.on('error', reject);
        incoming.on('end', () => {
          const responseHeaders = new Headers();
          for (const [name, value] of Object.entries(incoming.headers)) {
            if (value !== undefined) responseHeaders.set(name, String(value));
          }
          agent.destroy();
          serverSide.destroy();
          resolve(new Response(chunks.length ? Buffer.concat(chunks) : null, {
            status: incoming.statusCode,
            headers: responseHeaders,
          }));
        });
      });
      client.on('error', reject);
      client.end(body);
    });
  }

  return { request, close };
}

function payload(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

const dune = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' };

test('health and empty collection return JSON', async (t) => {
  const { request } = start(t);
  const health = await request('/health');
  assert.equal(health.status, 200);
  assert.match(health.headers.get('content-type') ?? '', /^application\/json/);
  assert.deepEqual(await health.json(), { status: 'ok' });

  const books = await request('/books');
  assert.equal(books.status, 200);
  assert.deepEqual(await books.json(), []);
});

test('creates, reads, updates, and deletes a book', async (t) => {
  const { request } = start(t);
  const created = await request('/books', payload('POST', dune));
  assert.equal(created.status, 201);
  const book = await created.json();
  assert(Number.isSafeInteger(book.id));
  assert.deepEqual(book, { id: book.id, ...dune });

  const path = `/books/${book.id}`;
  assert.equal(created.headers.get('location'), path);
  const found = await request(path);
  assert.equal(found.status, 200);
  assert.deepEqual(await found.json(), book);

  const replacement = { title: 'Dune Messiah', author: dune.author };
  const updated = await request(path, payload('PUT', replacement));
  assert.equal(updated.status, 200);
  const expected = { id: book.id, ...replacement, year: null, isbn: null };
  assert.deepEqual(await updated.json(), expected);
  assert.deepEqual(await (await request(path)).json(), expected);

  const deleted = await request(path, { method: 'DELETE' });
  assert.equal(deleted.status, 204);
  assert.equal(await deleted.text(), '');
  for (const init of [undefined, payload('PUT', dune), { method: 'DELETE' }]) {
    const missing = await request(path, init);
    assert.equal(missing.status, 404);
    assert.deepEqual(await missing.json(), { error: 'Book not found' });
  }
});

test('filters the list by exact author', async (t) => {
  const { request } = start(t);
  const first = await request('/books', payload('POST', dune));
  assert.equal(first.status, 201);
  const book = await first.json();
  const second = await request('/books', payload('POST', { title: 'Kindred', author: 'Octavia Butler' }));
  assert.equal(second.status, 201);
  assert.equal((await (await request('/books')).json()).length, 2);

  const filtered = await request('/books?author=Frank%20Herbert');
  assert.equal(filtered.status, 200);
  assert.deepEqual(await filtered.json(), [book]);
  assert.deepEqual(await (await request('/books?author=frank%20herbert')).json(), []);
});

test('rejects invalid input without changing stored books', async (t) => {
  const { request } = start(t);
  for (const invalid of [
    { author: dune.author },
    { title: dune.title },
    { ...dune, title: ' ' },
    { ...dune, year: 1965.5 },
    { ...dune, isbn: 123 },
    [],
  ]) {
    const response = await request('/books', payload('POST', invalid));
    assert.equal(response.status, 400);
    assert.equal(typeof (await response.json()).error, 'string');
  }
  const malformed = await request('/books', { method: 'POST', body: '{' });
  assert.equal(malformed.status, 400);
  const tooLarge = await request('/books', payload('POST', { ...dune, title: 'a'.repeat(70 * 1024) }));
  assert.equal(tooLarge.status, 413);
  assert.deepEqual(await (await request('/books')).json(), []);
  assert.equal((await request('/books/1.5')).status, 400);

  const book = await (await request('/books', payload('POST', dune))).json();
  assert.equal((await request(`/books/${book.id}`, payload('PUT', { author: ' ' }))).status, 400);
  assert.deepEqual(await (await request('/books')).json(), [book]);
});

test('persists books when the server reopens its SQLite database', async (t) => {
  const directory = await mkdtemp(join(tmpdir(), 'books-api-'));
  try {
    const path = join(directory, 'books.sqlite');
    const first = start(t, path);
    const created = await first.request('/books', payload('POST', dune));
    assert.equal(created.status, 201);
    const book = await created.json();
    await first.close();

    const second = start(t, path);
    try {
      const found = await second.request(`/books/${book.id}`);
      assert.equal(found.status, 200);
      assert.deepEqual(await found.json(), book);
    } finally {
      await second.close();
    }
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
