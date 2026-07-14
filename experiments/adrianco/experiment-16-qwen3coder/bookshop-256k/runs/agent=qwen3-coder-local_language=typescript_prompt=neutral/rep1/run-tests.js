// This script runs tests without starting the server
const http = require('http');
const { books, nextId } = require('./index.js');

// Clear any existing data for clean tests
books.length = 0;
nextId = 1;

// Helper function to make HTTP requests for testing
function makeRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: 3000,
      path: path,
      method: method,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    if (data) {
      options.headers['Content-Length'] = Buffer.byteLength(JSON.stringify(data));
    }

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', chunk => {
        body += chunk.toString();
      });
      res.on('end', () => {
        try {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            data: JSON.parse(body)
          });
        } catch (e) {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            data: body
          });
        }
      });
    });

    req.on('error', reject);

    if (data) {
      req.write(JSON.stringify(data));
    }
    req.end();
  });
}

// Test functions
async function testHealthCheck() {
  console.log('Testing health check...');
  const response = await makeRequest('GET', '/health');
  console.log('Health check response:', response.data);
  console.assert(response.statusCode === 200, 'Health check should return 200');
  console.assert(response.data.status === 'OK', 'Health check should return OK status');
  console.log('✓ Health check passed');
}

async function testCreateBook() {
  console.log('\nTesting create book...');
  const bookData = {
    title: 'The Great Gatsby',
    author: 'F. Scott Fitzgerald',
    year: 1925,
    isbn: '978-0-7432-7356-5'
  };

  const response = await makeRequest('POST', '/books', bookData);
  console.log('Create book response:', response.data);
  
  console.assert(response.statusCode === 201, 'Create book should return 201');
  console.assert(response.data.title === bookData.title, 'Title should match');
  console.assert(response.data.author === bookData.author, 'Author should match');
  console.assert(response.data.year === bookData.year, 'Year should match');
  console.assert(response.data.isbn === bookData.isbn, 'ISBN should match');
  console.assert(response.data.id !== undefined, 'ID should be assigned');
  console.log('✓ Create book passed');
}

async function testGetAllBooks() {
  console.log('\nTesting get all books...');
  const response = await makeRequest('GET', '/books');
  console.log('Get all books response:', response.data);
  
  console.assert(response.statusCode === 200, 'Get all books should return 200');
  console.assert(Array.isArray(response.data), 'Response should be an array');
  console.assert(response.data.length > 0, 'Should have at least one book');
  console.log('✓ Get all books passed');
}

async function testGetBookById() {
  console.log('\nTesting get book by ID...');
  const response = await makeRequest('GET', '/books/1');
  console.log('Get book by ID response:', response.data);
  
  console.assert(response.statusCode === 200, 'Get book by ID should return 200');
  console.assert(response.data.id === 1, 'Should return the correct book');
  console.assert(response.data.title === 'The Great Gatsby', 'Should return correct title');
  console.log('✓ Get book by ID passed');
}

async function testUpdateBook() {
  console.log('\nTesting update book...');
  const updateData = {
    title: 'The Great Gatsby - Updated',
    author: 'F. Scott Fitzgerald',
    year: 1926,
    isbn: '978-0-7432-7356-6'
  };

  const response = await makeRequest('PUT', '/books/1', updateData);
  console.log('Update book response:', response.data);
  
  console.assert(response.statusCode === 200, 'Update book should return 200');
  console.assert(response.data.id === 1, 'Should update the correct book');
  console.assert(response.data.title === updateData.title, 'Title should be updated');
  console.assert(response.data.year === updateData.year, 'Year should be updated');
  console.log('✓ Update book passed');
}

async function testDeleteBook() {
  console.log('\nTesting delete book...');
  const response = await makeRequest('DELETE', '/books/1');
  console.log('Delete book response:', response.data);
  
  console.assert(response.statusCode === 200, 'Delete book should return 200');
  console.assert(response.data.message === 'Book deleted successfully', 'Should return success message');
  console.assert(response.data.book.id === 1, 'Should return deleted book');
  
  // Verify book is actually deleted
  const getResponse = await makeRequest('GET', '/books/1');
  console.assert(getResponse.statusCode === 404, 'Deleted book should not be found');
  console.log('✓ Delete book passed');
}

async function testValidation() {
  console.log('\nTesting validation...');
  
  // Test invalid book creation (missing title)
  const invalidBookData = {
    author: 'Some Author'
  };
  
  const response = await makeRequest('POST', '/books', invalidBookData);
  console.log('Validation response:', response.data);
  
  console.assert(response.statusCode === 400, 'Should return 400 for validation error');
  console.assert(response.data.errors !== undefined, 'Should have errors');
  console.log('✓ Validation passed');
}

async function testFilterByAuthor() {
  console.log('\nTesting filter by author...');
  
  // Create another book for filtering
  const bookData = {
    title: 'To Kill a Mockingbird',
    author: 'Harper Lee',
    year: 1960
  };
  
  await makeRequest('POST', '/books', bookData);
  
  // Filter by author
  const response = await makeRequest('GET', '/books?author=Harper');
  console.log('Filter by author response:', response.data);
  
  console.assert(response.statusCode === 200, 'Filter should return 200');
  console.assert(Array.isArray(response.data), 'Response should be an array');
  console.assert(response.data.length > 0, 'Should find at least one book');
  console.assert(response.data[0].author === 'Harper Lee', 'Should filter correctly');
  console.log('✓ Filter by author passed');
}

async function runAllTests() {
  console.log('Running tests...\n');
  
  try {
    await testHealthCheck();
    await testCreateBook();
    await testGetAllBooks();
    await testGetBookById();
    await testUpdateBook();
    await testDeleteBook();
    await testValidation();
    await testFilterByAuthor();
    
    console.log('\n🎉 All tests passed!');
  } catch (error) {
    console.error('\n❌ Test failed:', error);
    process.exit(1);
  }
}

// Run tests
runAllTests().catch(console.error);