import { app, dbPromise } from './app';
import http from 'http';

const PORT = 3000;

function request(method: string, path: string, body?: any): Promise<{ status: number; body: any }> {
  return new Promise((resolve, reject) => {
    const encodedPath = encodeURI(path);
    const options: any = {
      hostname: 'localhost',
      port: PORT,
      path: encodedPath,
      method,
      headers: { 'Content-Type': 'application/json' },
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        let parsed: any = '';
        try {
          parsed = JSON.parse(data);
        } catch (e) {
          parsed = data;
        }
        resolve({ status: res.statusCode || 500, body: parsed });
      });
    });

    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function runTests() {
  let passed = 0;
  let failed = 0;

  async function assert(name: string, condition: boolean) {
    if (condition) {
      console.log(`  ✓ ${name}`);
      passed++;
    } else {
      console.log(`  ✗ ${name}`);
      failed++;
    }
  }

  // Wait for DB to initialize
  await dbPromise;

  console.log('\n=== Book API Tests ===\n');

  // Test 1: Health check
  console.log('1. Health check');
  const health = await request('GET', '/health');
  await assert('status 200', health.status === 200);
  await assert('status ok', health.body.status === 'ok');

  // Test 2: Create a book
  console.log('\n2. Create a book');
  const create = await request('POST', '/books', {
    title: 'The Great Gatsby',
    author: 'F. Scott Fitzgerald',
    year: 1925,
    isbn: '978-0743273565',
  });
  await assert('status 201', create.status === 201);
  const bookId = create.body.id as number;
  await assert('has id', !!bookId);
  await assert('title correct', create.body.title === 'The Great Gatsby');
  await assert('author correct', create.body.author === 'F. Scott Fitzgerald');

  // Test 3: Create another book
  console.log('\n3. Create another book');
  const create2 = await request('POST', '/books', {
    title: '1984',
    author: 'George Orwell',
    year: 1949,
    isbn: '978-0451524935',
  });
  await assert('status 201', create2.status === 201);

  // Test 4: List all books
  console.log('\n4. List all books');
  const list = await request('GET', '/books');
  await assert('status 200', list.status === 200);
  await assert('has 2 books', Array.isArray(list.body) && list.body.length === 2);

  // Test 5: Filter by author
  console.log('\n5. Filter by author');
  const filtered = await request('GET', '/books?author=George Orwell');
  await assert('status 200', filtered.status === 200);
  await assert('has 1 book', Array.isArray(filtered.body) && filtered.body.length === 1);
  await assert('correct book', filtered.body[0].title === '1984');

  // Test 6: Get single book
  console.log('\n6. Get single book');
  const get = await request('GET', `/books/${bookId}`);
  await assert('status 200', get.status === 200);
  await assert('correct title', get.body.title === 'The Great Gatsby');

  // Test 7: Get non-existent book
  console.log('\n7. Get non-existent book');
  const notFound = await request('GET', '/books/9999');
  await assert('status 404', notFound.status === 404);

  // Test 8: Update a book
  console.log('\n8. Update a book');
  const update = await request('PUT', `/books/${bookId}`, {
    title: 'The Great Gatsby (Updated)',
  });
  await assert('status 200', update.status === 200);
  await assert('title updated', update.body.title === 'The Great Gatsby (Updated)');
  await assert('author unchanged', update.body.author === 'F. Scott Fitzgerald');

  // Test 9: Delete a book
  console.log('\n9. Delete a book');
  const del = await request('DELETE', `/books/${create2.body.id}`);
  await assert('status 204', del.status === 204);

  // Test 10: Verify deletion
  console.log('\n10. Verify deletion');
  const listAfter = await request('GET', '/books');
  await assert('has 1 book', Array.isArray(listAfter.body) && listAfter.body.length === 1);

  // Test 11: Validation - missing title
  console.log('\n11. Validation - missing title');
  const invalid = await request('POST', '/books', { author: 'Someone' });
  await assert('status 400', invalid.status === 400);

  // Test 12: Validation - missing author
  console.log('\n12. Validation - missing author');
  const invalid2 = await request('POST', '/books', { title: 'Something' });
  await assert('status 400', invalid2.status === 400);

  console.log(`\n=== Results: ${passed} passed, ${failed} failed ===\n`);

  process.exit(failed > 0 ? 1 : 0);
}

runTests().catch(console.error);
