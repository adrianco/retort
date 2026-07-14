const { app, startServer } = require('./app');
const request = require('supertest');
const { expect } = require('chai');

// Start server for testing
startServer();

// Test that the basic server is working
console.log("Testing API endpoints...");

// We'll run some basic tests to validate functionality
setTimeout(() => {
  // Test health endpoint
  request(app)
    .get('/health')
    .expect(200)
    .then(response => {
      console.log("✓ Health check working:", response.body.status);
      
      // Test POST /books
      const bookData = {
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890'
      };
      
      request(app)
        .post('/books')
        .send(bookData)
        .expect(201)
        .then(response => {
          console.log("✓ Book creation working:", response.body.title);
          
          // Test GET /books
          request(app)
            .get('/books')
            .expect(200)
            .then(response => {
              console.log("✓ Book listing working:", response.body.length, "books found");
              console.log("✓ All tests completed successfully");
            });
        });
    })
    .catch(err => {
      console.error("Test failed:", err.message);
    });
}, 1000);