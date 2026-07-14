const http = require('http');
const url = require('url');
const querystring = require('querystring');

// In-memory storage for books
let books = [];
let nextId = 1;

// Helper function to send JSON response
function sendJsonResponse(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  });
  res.end(JSON.stringify(data));
}

// Helper function to parse JSON body
function parseJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      try {
        const parsed = JSON.parse(body);
        resolve(parsed);
      } catch (e) {
        reject(e);
      }
    });
  });
}

// Helper function to validate book data
function validateBook(book) {
  const errors = [];
  if (!book.title || book.title.trim() === '') {
    errors.push('Title is required');
  }
  if (!book.author || book.author.trim() === '') {
    errors.push('Author is required');
  }
  return errors;
}

// Helper function to find book by ID
function findBookById(id) {
  return books.find(book => book.id === parseInt(id));
}

// Health check endpoint
function handleHealth(req, res) {
  sendJsonResponse(res, 200, { status: 'OK', message: 'Book API is running' });
}

// GET /books - List all books or filter by author
async function handleGetBooks(req, res) {
  const parsedUrl = url.parse(req.url);
  const queryParams = querystring.parse(parsedUrl.query);
  
  let filteredBooks = books;
  
  if (queryParams.author) {
    filteredBooks = books.filter(book => 
      book.author.toLowerCase().includes(queryParams.author.toLowerCase())
    );
  }
  
  sendJsonResponse(res, 200, filteredBooks);
}

// GET /books/:id - Get a single book by ID
async function handleGetBookById(req, res, id) {
  const book = findBookById(id);
  if (!book) {
    sendJsonResponse(res, 404, { error: 'Book not found' });
    return;
  }
  sendJsonResponse(res, 200, book);
}

// POST /books - Create a new book
async function handlePostBook(req, res) {
  try {
    const bookData = await parseJsonBody(req);
    
    // Validate input
    const errors = validateBook(bookData);
    if (errors.length > 0) {
      sendJsonResponse(res, 400, { errors });
      return;
    }
    
    // Create new book
    const newBook = {
      id: nextId++,
      title: bookData.title,
      author: bookData.author,
      year: bookData.year,
      isbn: bookData.isbn
    };
    
    books.push(newBook);
    sendJsonResponse(res, 201, newBook);
  } catch (error) {
    sendJsonResponse(res, 400, { error: 'Invalid JSON data' });
  }
}

// PUT /books/:id - Update a book
async function handlePutBook(req, res, id) {
  const book = findBookById(id);
  if (!book) {
    sendJsonResponse(res, 404, { error: 'Book not found' });
    return;
  }
  
  try {
    const bookData = await parseJsonBody(req);
    
    // Validate input - title and author required
    const errors = validateBook(bookData);
    if (errors.length > 0) {
      sendJsonResponse(res, 400, { errors });
      return;
    }
    
    // Update book
    book.title = bookData.title;
    book.author = bookData.author;
    book.year = bookData.year;
    book.isbn = bookData.isbn;
    
    sendJsonResponse(res, 200, book);
  } catch (error) {
    sendJsonResponse(res, 400, { error: 'Invalid JSON data' });
  }
}

// DELETE /books/:id - Delete a book
async function handleDeleteBook(req, res, id) {
  const index = books.findIndex(book => book.id === parseInt(id));
  if (index === -1) {
    sendJsonResponse(res, 404, { error: 'Book not found' });
    return;
  }
  
  const deletedBook = books.splice(index, 1)[0];
  sendJsonResponse(res, 200, { message: 'Book deleted successfully', book: deletedBook });
}

// Handle all requests
function handleRequest(req, res) {
  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    res.end();
    return;
  }
  
  const parsedUrl = url.parse(req.url);
  const path = parsedUrl.pathname;
  const method = req.method;
  
  // Route matching
  if (path === '/health' && method === 'GET') {
    handleHealth(req, res);
  } else if (path === '/books' && method === 'GET') {
    handleGetBooks(req, res);
  } else if (path === '/books' && method === 'POST') {
    handlePostBook(req, res);
  } else if (method === 'GET' && /^\/books\/\d+$/.test(path)) {
    const id = path.split('/').pop();
    handleGetBookById(req, res, id);
  } else if (method === 'PUT' && /^\/books\/\d+$/.test(path)) {
    const id = path.split('/').pop();
    handlePutBook(req, res, id);
  } else if (method === 'DELETE' && /^\/books\/\d+$/.test(path)) {
    const id = path.split('/').pop();
    handleDeleteBook(req, res, id);
  } else {
    sendJsonResponse(res, 404, { error: 'Endpoint not found' });
  }
}

// Export functions for testing
module.exports = {
  books,
  nextId,
  handleRequest,
  sendJsonResponse,
  validateBook,
  findBookById
};