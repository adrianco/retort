const { books, nextId, handleRequest } = require('./app.js');
const http = require('http');
const url = require('url');

// Clear any existing data for clean tests
books.length = 0;
let testNextId = 1;

// Mock request and response objects for testing
function createMockRequest(method, path, bodyData = null) {
  const mockReq = {
    method: method,
    url: path,
    headers: {
      'content-type': 'application/json'
    },
    on: function(event, callback) {
      if (event === 'data') {
        if (bodyData) {
          callback(JSON.stringify(bodyData));
        }
      }
      if (event === 'end') {
        setImmediate(callback);
      }
    },
    emit: function(event, ...args) {
      if (event === 'error') {
        console.error('Request error:', args[0]);
      }
    }
  };

  // Mock the URL parsing
  mockReq.url = path;
  return mockReq;
}

function createMockResponse() {
  const response = {
    statusCode: null,
    headers: {},
    writeHead: function(statusCode, headers) {
      this.statusCode = statusCode;
      this.headers = headers;
    },
    end: function(data) {
      this.data = data;
      this.resolved = true;
    },
    write: function(chunk) {
      if (!this.buffer) this.buffer = '';
      this.buffer += chunk;
    }
  };
  
  return response;
}

// Test functions
async function testHealthCheck() {
  console.log('Testing health check...');
  
  const req = createMockRequest('GET', '/health');
  const res = createMockResponse();
  
  handleRequest(req, res);
  
  // Since this is synchronous, we can directly test
  const result = JSON.parse(res.data);
  console.log('Health check response:', result);
  console.assert(res.statusCode === 200, 'Health check should return 200');
  console.assert(result.status === 'OK', 'Health check should return OK status');
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

  const req = createMockRequest('POST', '/books', bookData);
  const res = createMockResponse();
  
  handleRequest(req, res);
  
  const result = JSON.parse(res.data);
  console.log('Create book response:', result);
  
  console.assert(res.statusCode === 201, 'Create book should return 201');
  console.assert(result.title === bookData.title, 'Title should match');
  console.assert(result.author === bookData.author, 'Author should match');
  console.assert(result.year === bookData.year, 'Year should match');
  console.assert(result.isbn === bookData.isbn, 'ISBN should match');
  console.assert(result.id !== undefined, 'ID should be assigned');
  console.log('✓ Create book passed');
}

async function testGetAllBooks() {
  console.log('\nTesting get all books...');
  
  const req = createMockRequest('GET', '/books');
  const res = createMockResponse();
  
  handleRequest(req, res);
  
  const result = JSON.parse(res.data);
  console.log('Get all books response:', result);
  
  console.assert(res.statusCode === 200, 'Get all books should return 200');
  console.assert(Array.isArray(result), 'Response should be an array');
  console.assert(result.length > 0, 'Should have at least one book');
  console.log('✓ Get all books passed');
}

async function testGetBookById() {
  console.log('\nTesting get book by ID...');
  
  const req = createMockRequest('GET', '/books/1');
  const res = createMockResponse();
  
  handleRequest(req, res);
  
  const result = JSON.parse(res.data);
  console.log('Get book by ID response:', result);
  
  console.assert(res.statusCode === 200, 'Get book by ID should return 200');
  console.assert(result.id === 1, 'Should return the correct book');
  console.assert(result.title === 'The Great Gatsby', 'Should return correct title');
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

  const req = createMockRequest('PUT', '/books/1', updateData);
  const res = createMockResponse();
  
  handleRequest(req, res);
  
  const result = JSON.parse(res.data);
  console.log('Update book response:', result);
  
  console.assert(res.statusCode === 200, 'Update book should return 200');
  console.assert(result.id === 1, 'Should update the correct book');
  console.assert(result.title === updateData.title, 'Title should be updated');
  console.assert(result.year === updateData.year, 'Year should be updated');
  console.log('✓ Update book passed');
}

async function testDeleteBook() {
  console.log('\nTesting delete book...');
  
  const req = createMockRequest('DELETE', '/books/1');
  const res = createMockResponse();
  
  handleRequest(req, res);
  
  const result = JSON.parse(res.data);
  console.log('Delete book response:', result);
  
  console.assert(res.statusCode === 200, 'Delete book should return 200');
  console.assert(result.message === 'Book deleted successfully', 'Should return success message');
  console.assert(result.book.id === 1, 'Should return deleted book');
  
  // Verify book is actually deleted by trying to retrieve it
  const getReq = createMockRequest('GET', '/books/1');
  const getRes = createMockResponse();
  
  handleRequest(getReq, getRes);
  
  console.assert(getRes.statusCode === 404, 'Deleted book should not be found');
  console.log('✓ Delete book passed');
}

async function testValidation() {
  console.log('\nTesting validation...');
  
  // Test invalid book creation (missing title)
  const invalidBookData = {
    author: 'Some Author'
  };
  
  const req = createMockRequest('POST', '/books', invalidBookData);
  const res = createMockResponse();
  
  handleRequest(req, res);
  
  const result = JSON.parse(res.data);
  console.log('Validation response:', result);
  
  console.assert(res.statusCode === 400, 'Should return 400 for validation error');
  console.assert(result.errors !== undefined, 'Should have errors');
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
  
  const req = createMockRequest('POST', '/books', bookData);
  const res = createMockResponse();
  
  handleRequest(req, res);
  
  // Filter by author
  const filterReq = createMockRequest('GET', '/books?author=Harper');
  const filterRes = createMockResponse();
  
  handleRequest(filterReq, filterRes);
  
  const result = JSON.parse(filterRes.data);
  console.log('Filter by author response:', result);
  
  console.assert(filterRes.statusCode === 200, 'Filter should return 200');
  console.assert(Array.isArray(result), 'Response should be an array');
  console.assert(result.length > 0, 'Should find at least one book');
  console.assert(result[0].author === 'Harper Lee', 'Should filter correctly');
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