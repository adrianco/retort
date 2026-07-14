// Simple demonstration of the API functionality
const request = require('supertest');
const app = require('./server');

async function demo() {
  console.log('=== Book API Demo ===\n');
  
  // Test health check
  console.log('1. Testing health check...');
  const healthResponse = await request(app).get('/health');
  console.log(`   Status: ${healthResponse.status}`);
  console.log(`   Response: ${JSON.stringify(healthResponse.body, null, 2)}\n`);
  
  // Create some books
  console.log('2. Creating books...');
  const book1 = {
    title: 'The Great Gatsby',
    author: 'F. Scott Fitzgerald',
    year: 1925,
    isbn: '978-0-7432-7356-5'
  };
  
  const createResponse1 = await request(app)
    .post('/books')
    .send(book1)
    .expect(201);
  console.log(`   Created book: ${createResponse1.body.title} (ID: ${createResponse1.body.id})`);
  
  const book2 = {
    title: '1984',
    author: 'George Orwell',
    year: 1948
  };
  
  const createResponse2 = await request(app)
    .post('/books')
    .send(book2)
    .expect(201);
  console.log(`   Created book: ${createResponse2.body.title} (ID: ${createResponse2.body.id})\n`);
  
  // Get all books
  console.log('3. Getting all books...');
  const allBooksResponse = await request(app).get('/books');
  console.log(`   Found ${allBooksResponse.body.length} books`);
  allBooksResponse.body.forEach(book => {
    console.log(`   - ${book.title} by ${book.author} (${book.year || 'N/A'})`);
  });
  console.log();
  
  // Get a specific book
  console.log('4. Getting a specific book...');
  const bookId = createResponse1.body.id;
  const specificBookResponse = await request(app).get(`/books/${bookId}`);
  console.log(`   Found book: ${specificBookResponse.body.title} by ${specificBookResponse.body.author}`);
  console.log();
  
  // Update a book
  console.log('5. Updating a book...');
  const updateData = {
    title: 'The Great Gatsby - Updated',
    author: 'F. Scott Fitzgerald',
    year: 1925,
    isbn: '978-0-7432-7356-5'
  };
  
  const updateResponse = await request(app)
    .put(`/books/${bookId}`)
    .send(updateData)
    .expect(200);
  console.log(`   Updated book: ${updateResponse.body.title}`);
  console.log();
  
  // Delete a book
  console.log('6. Deleting a book...');
  const deleteResponse = await request(app).delete(`/books/${bookId}`);
  console.log(`   Status: ${deleteResponse.status}`);
  console.log(`   Message: ${deleteResponse.body.message}`);
  console.log();
  
  // Try to get deleted book
  console.log('7. Attempting to get deleted book...');
  const deletedBookResponse = await request(app).get(`/books/${bookId}`);
  console.log(`   Status: ${deletedBookResponse.status} (expected 404)`);
  
  console.log('\n=== Demo Complete ===');
}

// Run demo if script is executed directly
if (require.main === module) {
  demo().catch(console.error);
}

module.exports = demo;