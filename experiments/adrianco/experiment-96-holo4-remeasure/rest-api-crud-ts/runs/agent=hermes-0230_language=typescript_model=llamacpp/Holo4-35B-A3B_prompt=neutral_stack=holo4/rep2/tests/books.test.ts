import request from 'supertest';
import { app } from '../src/app';
import { db } from '../src/database';

const server = app;

// Clear books table before each test
function clearDb() {
  db.prepare('DELETE FROM books').run();
}

let passed = 0;
let failed = 0;

function assert(condition: boolean, msg: string) {
  if (!condition) {
    console.error(`  FAIL: ${msg}`);
    failed++;
  } else {
    passed++;
  }
}

async function run(name: string, fn: () => Promise<void>) {
  console.log(`  ${name}`);
  try {
    await fn();
  } catch (e: any) {
    console.error(`  ERROR: ${e.message}`);
    failed++;
  }
}

async function main() {
  console.log('Running tests...\n');

  // GET /health
  console.log('GET /health');
  {
    clearDb();
    const res = await request(server).get('/health');
    assert(res.status === 200, `expected 200, got ${res.status}`);
    assert(JSON.stringify(res.body) === JSON.stringify({ status: 'ok' }), `unexpected body: ${JSON.stringify(res.body)}`);
  }

  // POST /books
  console.log('POST /books');
  {
    clearDb();
    const res = await request(server)
      .post('/books')
      .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
    assert(res.status === 201, `expected 201, got ${res.status}`);
    assert(res.body.title === 'The Great Gatsby', `unexpected title: ${res.body.title}`);
    assert(res.body.author === 'F. Scott Fitzgerald', `unexpected author: ${res.body.author}`);
    assert(res.body.year === 1925, `unexpected year: ${res.body.year}`);
    assert(res.body.isbn === '978-0743273565', `unexpected isbn: ${res.body.isbn}`);
    assert(res.body.id !== undefined, 'expected id to be defined');
  }
  {
    clearDb();
    const res = await request(server).post('/books').send({ author: 'Someone' });
    assert(res.status === 400, `expected 400, got ${res.status}`);
    assert(res.body.error === 'title and author are required', `unexpected error: ${res.body.error}`);
  }

  // GET /books
  console.log('GET /books');
  {
    clearDb();
    await request(server).post('/books').send({ title: 'Book 1', author: 'Author A' });
    await request(server).post('/books').send({ title: 'Book 2', author: 'Author B' });
    const res = await request(server).get('/books');
    assert(res.status === 200, `expected 200, got ${res.status}`);
    assert(res.body.length === 2, `expected 2 books, got ${res.body.length}`);
  }
  {
    clearDb();
    await request(server).post('/books').send({ title: 'Book 1', author: 'Author A' });
    await request(server).post('/books').send({ title: 'Book 2', author: 'Author A' });
    await request(server).post('/books').send({ title: 'Book 3', author: 'Author B' });
    const res = await request(server).get('/books?author=Author A');
    assert(res.status === 200, `expected 200, got ${res.status}`);
    assert(res.body.length === 2, `expected 2 books, got ${res.body.length}`);
    assert(res.body[0].author === 'Author A', `unexpected author: ${res.body[0].author}`);
  }

  // GET /books/:id
  console.log('GET /books/:id');
  {
    clearDb();
    const createRes = await request(server).post('/books').send({ title: 'Test Book', author: 'Test Author' });
    const id = createRes.body.id;
    const res = await request(server).get(`/books/${id}`);
    assert(res.status === 200, `expected 200, got ${res.status}`);
    assert(res.body.title === 'Test Book', `unexpected title: ${res.body.title}`);
  }
  {
    clearDb();
    const res = await request(server).get('/books/99999');
    assert(res.status === 404, `expected 404, got ${res.status}`);
  }

  // PUT /books/:id
  console.log('PUT /books/:id');
  {
    clearDb();
    const createRes = await request(server).post('/books').send({ title: 'Old Title', author: 'Author' });
    const id = createRes.body.id;
    const res = await request(server).put(`/books/${id}`).send({ title: 'New Title' });
    assert(res.status === 200, `expected 200, got ${res.status}`);
    assert(res.body.title === 'New Title', `unexpected title: ${res.body.title}`);
  }
  {
    clearDb();
    const res = await request(server).put('/books/99999').send({ title: 'X' });
    assert(res.status === 404, `expected 404, got ${res.status}`);
  }

  // DELETE /books/:id
  console.log('DELETE /books/:id');
  {
    clearDb();
    const createRes = await request(server).post('/books').send({ title: 'Delete Me', author: 'Author' });
    const id = createRes.body.id;
    const res = await request(server).delete(`/books/${id}`);
    assert(res.status === 204, `expected 204, got ${res.status}`);
    const getRes = await request(server).get(`/books/${id}`);
    assert(getRes.status === 404, `expected 404 after delete, got ${getRes.status}`);
  }
  {
    clearDb();
    const res = await request(server).delete('/books/99999');
    assert(res.status === 404, `expected 404, got ${res.status}`);
  }

  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

main();
