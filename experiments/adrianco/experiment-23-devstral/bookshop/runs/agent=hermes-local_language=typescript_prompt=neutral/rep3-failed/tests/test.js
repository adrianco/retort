const request = require('supertest');
const assert = require('assert');
const { app, initializeDB } = require('../src-js/index');
const sqlite3 = require('sqlite3');
const { open } = require('sqlite');

(async function() {
  console.log('Initializing database...');
  await initializeDB();
  console.log('Database initialized.');
  
  let db = await open({
    filename: './books.db',
    driver: sqlite3.Database
  });
  
  // Clean up the database before tests
  await db.exec('DELETE FROM books');
  console.log('Database cleaned up.');
  
  // Test 1: Create a new book
  console.log('Testing book creation...');
  const res1 = await request(app)
    .post('/books')
    .send({
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '9780743273565'
    });
  
  assert.strictEqual(res1.status, 201);
  assert.ok(res1.body.id);
  assert.strictEqual(res1.body.title, 'The Great Gatsby');
  console.log('Book creation test passed.');
  
  // Test 2: Get all books
  console.log('Testing get all books...');
  const res2 = await request(app).get('/books');
  assert.strictEqual(res2.status, 200);
  assert.ok(Array.isArray(res2.body));
  console.log('Get all books test passed.');
  
  // Test 3: Get a book by ID
  console.log('Testing get book by ID...');
  const res3 = await request(app).get('/books/' + res1.body.id);
  assert.strictEqual(res3.status, 200);
  assert.strictEqual(res3.body.title, 'The Great Gatsby');
  console.log('Get book by ID test passed.');
  
  // Test 4: Update a book
  console.log('Testing book update...');
  const res4 = await request(app)
    .put('/books/' + res1.body.id)
    .send({
      title: 'The Great Gatsby (Updated)',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '9780743273565'
    });
  
  assert.strictEqual(res4.status, 200);
  assert.strictEqual(res4.body.title, 'The Great Gatsby (Updated)');
  console.log('Book update test passed.');
  
  // Test 5: Delete a book
  console.log('Testing book deletion...');
  const res5 = await request(app).delete('/books/' + res1.body.id);
  assert.strictEqual(res5.status, 204);
  
  // Verify it's deleted
  const res6 = await request(app).get('/books/' + res1.body.id);
  assert.strictEqual(res6.status, 404);
  console.log('Book deletion test passed.');
  
  // Test 6: Health check
  console.log('Testing health check...');
  const res7 = await request(app).get('/health');
  assert.strictEqual(res7.status, 200);
  assert.deepStrictEqual(res7.body, { status: 'OK' });
  console.log('Health check test passed.');
  
  console.log('All tests passed!');
})();
