import { app } from './index';
import { db } from './db';
import http from 'http';

const BASE = `http://localhost:${process.env.PORT || 3000}`;

interface FetchResponse {
  status: number;
  body: any;
  headers: any;
}

function fetch(url: string, options: any = {}): Promise<FetchResponse> {
  const parsed = new URL(url);
  const isAbsolute = url.startsWith('http');
  const target = isAbsolute ? parsed : new URL(url, BASE);
  const opts: any = {
    hostname: target.hostname,
    port: target.port,
    path: target.pathname + target.search,
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  };
  return new Promise((resolve, reject) => {
    const req = http.request(opts, (res) => {
      let body = '';
      res.on('data', (chunk: string) => (body += chunk));
      res.on('end', () => {
        let parsedBody: any = body;
        if (res.headers['content-type']?.includes('application/json')) {
          try { parsedBody = JSON.parse(body); } catch {}
        }
        resolve({ status: res.statusCode!, body: parsedBody, headers: res.headers });
      });
    });
    req.on('error', reject);
    if (options.body) req.write(JSON.stringify(options.body));
    req.end();
  });
}

let passed = 0;
let failed = 0;

async function assert(condition: boolean, name: string) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${name}`);
  } else {
    failed++;
    console.log(`  ✗ ${name}`);
  }
}

async function run() {
  // Clean up any existing data
  db.prepare('DELETE FROM books').run();

  console.log('\n--- Health Check ---');
  const health = await fetch(`${BASE}/health`);
  await assert(health.status === 200, 'GET /health returns 200');
  await assert(health.body.status === 'ok', 'Health status is ok');

  console.log('\n--- Create Book ---');
  const createRes = await fetch(`${BASE}/books`, {
    method: 'POST',
    body: { title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' },
  });
  await assert(createRes.status === 201, 'POST /books returns 201');
  await assert(createRes.body.title === 'The Great Gatsby', 'Created book has correct title');
  await assert(createRes.body.id !== undefined, 'Created book has an id');

  console.log('\n--- Validation ---');
  const badCreate = await fetch(`${BASE}/books`, {
    method: 'POST',
    body: { author: 'No Title' },
  });
  await assert(badCreate.status === 400, 'POST without title returns 400');

  const badCreate2 = await fetch(`${BASE}/books`, {
    method: 'POST',
    body: { title: 'No Author' },
  });
  await assert(badCreate2.status === 400, 'POST without author returns 400');

  console.log('\n--- Get Single Book ---');
  const getBook = await fetch(`${BASE}/books/1`);
  await assert(getBook.status === 200, 'GET /books/1 returns 200');
  await assert(getBook.body.id === 1, 'Book id is 1');

  const notFound = await fetch(`${BASE}/books/999`);
  await assert(notFound.status === 404, 'GET /books/999 returns 404');

  console.log('\n--- List Books ---');
  const listRes = await fetch(`${BASE}/books`);
  await assert(listRes.status === 200, 'GET /books returns 200');
  await assert(Array.isArray(listRes.body), 'Books is an array');
  await assert(listRes.body.length >= 1, 'At least one book in list');

  // Add a second book by the same author
  await fetch(`${BASE}/books`, {
    method: 'POST',
    body: { title: 'Tender Is the Night', author: 'F. Scott Fitzgerald', year: 1934 },
  });
  const filtered = await fetch(`${BASE}/books?author=F. Scott Fitzgerald`);
  await assert(filtered.status === 200, 'GET /books?author= returns 200');
  await assert(filtered.body.length === 2, 'Filtered list has 2 books');

  console.log('\n--- Update Book ---');
  const updateRes = await fetch(`${BASE}/books/1`, {
    method: 'PUT',
    body: { title: 'The Great Gatsby (Updated)' },
  });
  await assert(updateRes.status === 200, 'PUT /books/1 returns 200');
  await assert(updateRes.body.title === 'The Great Gatsby (Updated)', 'Title was updated');

  console.log('\n--- Delete Book ---');
  const delRes = await fetch(`${BASE}/books/1`, { method: 'DELETE' });
  await assert(delRes.status === 204, 'DELETE /books/1 returns 204');
  const stillThere = await fetch(`${BASE}/books/1`);
  await assert(stillThere.status === 404, 'Deleted book returns 404');

  db.prepare('DELETE FROM books').run();
  console.log(`\nResults: ${passed} passed, ${failed} failed\n`);
  process.exit(failed > 0 ? 1 : 0);
}

// Start server, run tests, then shut down
const server = app.listen(3000, () => {
  run().finally(() => server.close());
});
