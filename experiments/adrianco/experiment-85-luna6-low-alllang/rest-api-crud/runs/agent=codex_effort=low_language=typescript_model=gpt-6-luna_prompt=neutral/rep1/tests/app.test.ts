import { DatabaseSync } from 'node:sqlite';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { createApp } from '../src/app';

describe('book collection API', () => {
  let database: DatabaseSync;
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    database = new DatabaseSync(':memory:');
    app = createApp(database);
  });

  afterEach(() => database.close());

  async function call(method: string, path: string, body?: unknown) {
    const queryString = path.split('?')[1] ?? '';
    const pathname = path.split('?')[0];
    const layers = (app as any)._router.stack;
    const layer = layers.find((item: any) => item.route?.path && item.route.methods[method.toLowerCase()] &&
      (typeof item.route.path === 'string' ? item.route.path : '').split('/').length === pathname.split('/').length &&
      (typeof item.route.path === 'string' ? item.route.path : '').split('/').every((part: string, index: number) => part.startsWith(':') || part === pathname.split('/')[index]));
    if (!layer) throw new Error(`No route for ${method} ${pathname}`);
    const routePath = layer.route.path as string;
    const idMatch = routePath.includes(':id') ? pathname.match(/\/books\/([^/]+)$/) : null;
    const req: any = { method, url: path, originalUrl: path, path: pathname, query: Object.fromEntries(new URLSearchParams(queryString)), params: idMatch ? { id: idMatch[1] } : {}, body };
    const response: { status: number; body: any } = { status: 200, body: undefined };
    const res: any = {
      status(code: number) { response.status = code; return this; },
      json(value: unknown) { response.body = value; return this; },
      end() { return this; },
    };
    const handlers = layer.route.stack.map((entry: any) => entry.handle);
    for (const handler of handlers) {
      if (handler.length === 4) continue;
      await handler(req, res, (error?: unknown) => { if (error) throw error; });
    }
    return response;
  }

  it('reports health and creates a book', async () => {
    expect((await call('GET', '/health')).status).toBe(200);
    const response = await call('POST', '/books', { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' });
    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({ id: 1, title: 'Dune', author: 'Frank Herbert', year: 1965 });
  });

  it('requires title and author', async () => {
    const response = await call('POST', '/books', { title: 'Dune' });
    expect(response.status).toBe(400);
    expect(response.body.error).toBe('author is required');
  });

  it('lists books with a case-insensitive author filter', async () => {
    await call('POST', '/books', { title: 'Dune', author: 'Frank Herbert' });
    await call('POST', '/books', { title: 'Foundation', author: 'Isaac Asimov' });
    const response = await call('GET', '/books?author=frank%20herbert');
    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0].title).toBe('Dune');
  });

  it('gets, updates, and deletes a book', async () => {
    const created = await call('POST', '/books', { title: 'Dune', author: 'Frank Herbert' });
    const id = created.body.id;
    expect((await call('GET', `/books/${id}`)).status).toBe(200);
    const updated = await call('PUT', `/books/${id}`, { title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 });
    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe('Dune Messiah');
    expect((await call('DELETE', `/books/${id}`)).status).toBe(204);
    expect((await call('GET', `/books/${id}`)).status).toBe(404);
  });
});
