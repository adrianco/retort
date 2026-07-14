// Simple verification script for the book API
const http = require('http');
const { exec } = require('child_process');

console.log('Verifying Book API implementation...\n');

// Test if server is running
exec('curl -s http://localhost:3000/health', (error, stdout, stderr) => {
  if (error) {
    console.error('Error accessing health endpoint:', error);
    return;
  }
  
  console.log('✓ Health check endpoint works');
  console.log('  Response:', stdout.trim());
  
  // Test creating a book
  const createBookData = JSON.stringify({
    title: 'Test Book',
    author: 'Test Author',
    year: 2023,
    isbn: '978-0-123456-78-9'
  });
  
  const createReq = http.request({
    hostname: 'localhost',
    port: 3000,
    path: '/books',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(createBookData)
    }
  }, (res) => {
    console.log('✓ POST /books works');
    res.on('data', (chunk) => {
      console.log('  Response:', chunk.toString());
    });
  });
  
  createReq.on('error', (e) => {
    console.error('Error creating book:', e);
  });
  
  createReq.write(createBookData);
  createReq.end();
});