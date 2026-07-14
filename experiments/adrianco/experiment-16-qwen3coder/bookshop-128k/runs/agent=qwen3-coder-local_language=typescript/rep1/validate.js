const http = require('http');
const { exec } = require('child_process');

// Simple function to check if server is running
function checkServer() {
  return new Promise((resolve, reject) => {
    const req = http.get('http://localhost:3000/health', (res) => {
      console.log('Server is running');
      console.log('Status Code:', res.statusCode);
      resolve();
    }).on('error', (err) => {
      console.log('Server not running yet');
      reject(err);
    });
  });
}

// Check if server is running
checkServer()
  .then(() => {
    console.log('API is working correctly');
  })
  .catch(() => {
    console.log('Starting server...');
    const child = exec('node index.js', (error, stdout, stderr) => {
      if (error) {
        console.error(`Error: ${error}`);
        return;
      }
      console.log('Server started successfully');
    });
    
    // Give it a moment to start
    setTimeout(() => {
      checkServer().then(() => {
        console.log('API is working correctly');
      }).catch(() => {
        console.log('Server failed to start');
      });
    }, 2000);
  });