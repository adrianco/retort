const http = require('http');
const { exec } = require('child_process');

// Function to make HTTP requests
function makeRequest(method, path, data = null) {
  const options = {
    hostname: 'localhost',
    port: 3000,
    path: path,
    method: method,
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': data ? Buffer.byteLength(data) : 0
    }
  };

  return new Promise((resolve, reject) => {
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
            body: JSON.parse(body)
          });
        } catch (e) {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            body: body
          });
        }
      });
    });
    
    req.on('error', reject);
    
    if (data) {
      req.write(data);
    }
    req.end();
  });
}

// Test the API
async function testAPI() {
  console.log('Testing Book API...\n');
  
  // Test health check
  console.log('1. Testing health check...');
  try {
    const health = await makeRequest('GET', '/health');
    console.log('   Status:', health.statusCode);
    console.log('   Response:', health.body);
  } catch (error) {
    console.log('   Error:', error.message);
  }
  
  // Test creating a book
  console.log('\n2. Testing book creation...');
  try {
    const bookData = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };
    
    const createResponse = await makeRequest('POST', '/books', JSON.stringify(bookData));
    console.log('   Status:', createResponse.statusCode);
    console.log('   Created book:', createResponse.body);
  } catch (error) {
    console.log('   Error:', error.message);
  }
  
  // Test listing books
  console.log('\n3. Testing listing books...');
  try {
    const listResponse = await makeRequest('GET', '/books');
    console.log('   Status:', listResponse.statusCode);
    console.log('   Books:', listResponse.body);
  } catch (error) {
    console.log('   Error:', error.message);
  }
  
  // Test getting a book by ID
  console.log('\n4. Testing get book by ID...');
  try {
    const getResponse = await makeRequest('GET', '/books/1');
    console.log('   Status:', getResponse.statusCode);
    console.log('   Book:', getResponse.body);
  } catch (error) {
    console.log('   Error:', error.message);
  }
  
  console.log('\nTest completed.');
}

// Run the test
testAPI().catch(console.error);
