import http from 'http';
import express from 'express';
import { resetDb } from '../database';
import { handleError, parseBody } from '../middleware';

const BASE_URLS: string[] = [];

function request(method: string, baseUrl: string, path: string, body?: any): Promise<{ status: number; data: any }> {
  return new Promise((resolve, reject) => {
    const url = new URL(path, baseUrl);
    const options: any = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method,
      headers: { 'Content-Type': 'application/json' },
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode || 0, data: data ? JSON.parse(data) : null });
        } catch {
          resolve({ status: res.statusCode || 0, data });
        }
      });
    });
    req.on('error', reject);
    if (body !== undefined) req.write(JSON.stringify(body));
    req.end();
  });
}

let app: express.Express;
let server: http.Server;

function createApp() {
  const a = express();
  a.use(parseBody);
  a.get('/health', (req: any, res: any) => {
    res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
  });
  const bookRoutes = require('../routes').default;
  a.use('/', bookRoutes);
  a.use(handleError);
  return a;
}

beforeAll((done) => {
  // Reset DB at the start of the test suite
  resetDb();
  app = createApp();
  server = app.listen(0, () => {
    const addr = server!.address();
    if (addr && typeof addr === 'object') {
      BASE_URLS.push(`http://localhost:${addr.port}`);
    }
    done();
  });
});

afterAll((done) => {
  if (server) server.close(done);
  else done();
});

function getBase() {
  return BASE_URLS[0] || 'http://localhost:3000';
}

describe('Book API', () => {
  describe('GET /health', () => {
    it('returns 200 with status ok', async () => {
      const res = await request('GET', getBase(), '/health');
      expect(res.status).toBe(200);
      expect(res.data.status).toBe('ok');
      expect(res.data.timestamp).toBeDefined();
    });
  });

  describe('POST /books', () => {
    it('creates a book and returns 201', async () => {
      const res = await request('POST', getBase(), '/books', {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      });
      expect(res.status).toBe(201);
      expect(res.data.id).toBeDefined();
      expect(res.data.title).toBe('The Great Gatsby');
      expect(res.data.author).toBe('F. Scott Fitzgerald');
      expect(res.data.year).toBe(1925);
      expect(res.data.isbn).toBe('978-0743273565');
    });

    it('returns 400 for missing title', async () => {
      const res = await request('POST', getBase(), '/books', {
        author: 'Test Author',
        year: 2020,
        isbn: '1234567890',
      });
      expect(res.status).toBe(400);
      expect(res.data.error).toBe('Validation error');
    });

    it('returns 400 for missing author', async () => {
      const res = await request('POST', getBase(), '/books', {
        title: 'Test Book',
        year: 2020,
        isbn: '1234567890',
      });
      expect(res.status).toBe(400);
      expect(res.data.error).toBe('Validation error');
    });

    it('returns 400 for missing year', async () => {
      const res = await request('POST', getBase(), '/books', {
        title: 'Test Book',
        author: 'Test Author',
        isbn: '1234567890',
      });
      expect(res.status).toBe(400);
      expect(res.data.error).toBe('Validation error');
    });

    it('returns 409 for duplicate ISBN', async () => {
      const res = await request('POST', getBase(), '/books', {
        title: 'Another Book',
        author: 'Another Author',
        year: 2021,
        isbn: '978-0743273565',
      });
      expect(res.status).toBe(409);
    });
  });

  describe('GET /books', () => {
    it('lists all books', async () => {
      const res = await request('GET', getBase(), '/books');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.data)).toBe(true);
      expect(res.data.length).toBeGreaterThanOrEqual(1);
    });

    it('filters by author', async () => {
      const res = await request('GET', getBase(), '/books?author=F. Scott Fitzgerald');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.data)).toBe(true);
      expect(res.data.length).toBeGreaterThanOrEqual(1);
      res.data.forEach((book: any) => {
        expect(book.author).toBe('F. Scott Fitzgerald');
      });
    });
  });

  describe('GET /books/:id', () => {
    it('returns a book by ID', async () => {
      const res = await request('GET', getBase(), '/books/1');
      expect(res.status).toBe(200);
      expect(res.data.id).toBe(1);
      expect(res.data.title).toBe('The Great Gatsby');
    });

    it('returns 404 for non-existent book', async () => {
      const res = await request('GET', getBase(), '/books/9999');
      expect(res.status).toBe(404);
      expect(res.data.error).toContain('not found');
    });
  });

  describe('PUT /books/:id', () => {
    it('updates a book', async () => {
      const res = await request('PUT', getBase(), '/books/1', {
        title: 'The Great Gatsby (Updated)',
      });
      expect(res.status).toBe(200);
      expect(res.data.title).toBe('The Great Gatsby (Updated)');
      expect(res.data.author).toBe('F. Scott Fitzgerald');
    });

    it('returns 404 for non-existent book', async () => {
      const res = await request('PUT', getBase(), '/books/9999', { title: 'Nope' });
      expect(res.status).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes a book and returns 204', async () => {
      const res = await request('DELETE', getBase(), '/books/1');
      expect(res.status).toBe(204);
    });

    it('returns 404 for non-existent book', async () => {
      const res = await request('DELETE', getBase(), '/books/9999');
      expect(res.status).toBe(404);
    });
  });
});
