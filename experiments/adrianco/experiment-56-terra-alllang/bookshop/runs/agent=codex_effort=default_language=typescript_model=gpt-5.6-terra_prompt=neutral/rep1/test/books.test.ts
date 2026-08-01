import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Readable } from 'node:stream';
import { createApp } from '../src/app.ts';

function startApi() {
  const server = createApp({ databasePath: ':memory:' });

  return {
    request(path: string, init: { method?: string; body?: string } = {}) {
      return new Promise<{ status: number; headers: Record<string, string>; text(): Promise<string>; json(): Promise<unknown> }>((resolve) => {
        const request = Object.assign(Readable.from(init.body ? [init.body] : []), {
          method: init.method ?? 'GET',
          url: path
        });
        let status = 200;
        let headers: Record<string, string> = {};
        let body = '';
        const response = {
          writeHead(code: number, values: Record<string, string> = {}) {
            status = code;
            headers = values;
          },
          end(chunk?: string) {
            body += chunk ?? '';
            resolve({
              status,
              headers,
              text: async () => body,
              json: async () => JSON.parse(body) as unknown
            });
          }
        };
        server.emit('request', request, response);
      });
    },
    close() {
      server.emit('close');
    }
  };
}

function json(body: unknown): { method: string; body: string } {
  return {
    method: 'POST',
    body: JSON.stringify(body)
  };
}

test('health check and create/get book work through the HTTP handler', async () => {
  const api = startApi();
  try {
    const health = await api.request('/health');
    assert.equal(health.status, 200);
    assert.deepEqual(await health.json(), { status: 'ok' });

    const created = await api.request('/books', json({
      title: 'Kindred', author: 'Octavia Butler', year: 1979, isbn: '9780807083697'
    }));
    assert.equal(created.status, 201);
    assert.match(created.headers['content-type'] ?? '', /^application\/json/);
    const book = await created.json();
    assert.deepEqual(book, {
      id: 1, title: 'Kindred', author: 'Octavia Butler', year: 1979, isbn: '9780807083697'
    });

    const fetched = await api.request('/books/1');
    assert.equal(fetched.status, 200);
    assert.deepEqual(await fetched.json(), book);
  } finally {
    api.close();
  }
});

test('lists books and filters them by author', async () => {
  const api = startApi();
  try {
    await api.request('/books', json({ title: 'Parable of the Sower', author: 'Octavia Butler' }));
    await api.request('/books', json({ title: 'Dune', author: 'Frank Herbert' }));

    const all = await api.request('/books');
    assert.equal(all.status, 200);
    assert.equal((await all.json()).length, 2);

    const filtered = await api.request('/books?author=Octavia%20Butler');
    assert.equal(filtered.status, 200);
    assert.deepEqual(await filtered.json(), [{
      id: 1, title: 'Parable of the Sower', author: 'Octavia Butler', year: null, isbn: null
    }]);
  } finally {
    api.close();
  }
});

test('validates input and updates then deletes a book', async () => {
  const api = startApi();
  try {
    const invalid = await api.request('/books', json({ title: '' }));
    assert.equal(invalid.status, 400);
    assert.deepEqual(await invalid.json(), { error: 'title is required' });

    const created = await api.request('/books', json({ title: 'Dune', author: 'Frank Herbert' }));
    assert.equal(created.status, 201);

    const updated = await api.request('/books/1', {
      ...json({ year: 1965, isbn: '9780441172719' }),
      method: 'PUT'
    });
    assert.equal(updated.status, 200);
    assert.deepEqual(await updated.json(), {
      id: 1, title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719'
    });

    const deleted = await api.request('/books/1', { method: 'DELETE' });
    assert.equal(deleted.status, 204);
    assert.equal(await deleted.text(), '');

    const missing = await api.request('/books/1');
    assert.equal(missing.status, 404);
    assert.deepEqual(await missing.json(), { error: 'Book not found' });
  } finally {
    api.close();
  }
});
