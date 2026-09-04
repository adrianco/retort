#!/usr/bin/env node

const axios = require('axios');
const fs = require('fs');

// Base URL for the API
const BASE_URL = 'http://localhost:3000';

// Test function for making API requests
async function testEndpoint(method, url, data = null, expectedStatus = 200) {
  try {
    let response;
    switch (method.toLowerCase()) {
      case 'get':
        response = await axios.get(url);
        break;
      case 'post':
        response = await axios.post(url, data);
        break;
      case 'put':
        response = await axios.put(url, data);
        break;
      case 'delete':
        response = await axios.delete(url);
        break;
      default:
        throw new Error(`Unsupported method: ${method}`);
    }

    if (response.status !== expectedStatus) {
      console.error(`❌ ${method} ${url} - Expected status ${expectedStatus}, got ${response.status}`);
      return false;
    }
    
    console.log(`✅ ${method} ${url} - Status: ${response.status}`);
    return true;
  } catch (error) {
    if (error.response && error.response.status !== expectedStatus) {
      console.error(`❌ ${method} ${url} - Expected status ${expectedStatus}, got ${error.response.status}`);
      return false;
    }
    
    console.log(`✅ ${method} ${url} - Status: ${error.response.status}`);
    return true;
  }
}

async function runTests() {
  console.log('🧪 Running Book API Tests...\n');
  
  // Test health check endpoint
  console.log('1. Testing Health Check Endpoint');
  await testEndpoint('GET', `${BASE_URL}/health`, null, 200);
  
  // Test creating a book
  console.log('\n2. Testing Create Book');
  const newBook = {
    title: 'The Great Gatsby',
    author: 'F. Scott Fitzgerald',
    year: 1925,
    isbn: '978-0-7432-7356-5'
  };
  
  await testEndpoint('POST', `${BASE_URL}/books`, newBook, 201);
  
  // Test getting all books
  console.log('\n3. Testing Get All Books');
  await testEndpoint('GET', `${BASE_URL}/books`, null, 200);
  
  // Test filtering by author
  console.log('\n4. Testing Filter Books by Author');
  await testEndpoint('GET', `${BASE_URL}/books?author=Fitzgerald`, null, 200);
  
  // Test getting a single book
  console.log('\n5. Testing Get Single Book');
  // First, let's get the created book ID
  try {
    const getAllBooksResponse = await axios.get(`${BASE_URL}/books`);
    const createdBookId = getAllBooksResponse.data[0]?.id;
    if (createdBookId) {
      await testEndpoint('GET', `${BASE_URL}/books/${createdBookId}`, null, 200);
    }
  } catch (error) {
    console.log('Could not test single book retrieval');
  }
  
  // Test updating a book
  console.log('\n6. Testing Update Book');
  try {
    const getAllBooksResponse = await axios.get(`${BASE_URL}/books`);
    const bookId = getAllBooksResponse.data[0]?.id;
    if (bookId) {
      const updatedBook = {
        title: 'The Great Gatsby - Updated',
        author: 'F. Scott Fitzgerald',
        year: 1926,
        isbn: '978-0-7432-7356-6'
      };
      await testEndpoint('PUT', `${BASE_URL}/books/${bookId}`, updatedBook, 200);
    }
  } catch (error) {
    console.log('Could not test book update');
  }
  
  // Test deleting a book
  console.log('\n7. Testing Delete Book');
  try {
    const getAllBooksResponse = await axios.get(`${BASE_URL}/books`);
    const bookId = getAllBooksResponse.data[0]?.id;
    if (bookId) {
      await testEndpoint('DELETE', `${BASE_URL}/books/${bookId}`, null, 200);
    }
  } catch (error) {
    console.log('Could not test book deletion');
  }
  
  console.log('\n🧪 Test suite completed!');
}

// Run the tests
runTests().catch(error => {
  console.error('Error running tests:', error);
});