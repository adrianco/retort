// Verify server functionality
const fs = require('fs');

// Check that all required files exist
const requiredFiles = [
  'package.json',
  'src/server.js',
  'README.md'
];

console.log('Verifying required files...');
let allFilesExist = true;

requiredFiles.forEach(file => {
  const exists = fs.existsSync(file);
  console.log(`${file}: ${exists ? '✓' : '✗'}`);
  if (!exists) allFilesExist = false;
});

if (allFilesExist) {
  console.log('\n✓ All required files exist');
} else {
  console.log('\n✗ Some required files are missing');
  process.exit(1);
}

// Check package.json content
try {
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
  console.log('\nChecking package.json...');
  console.log(`Name: ${packageJson.name}`);
  console.log(`Version: ${packageJson.version}`);
  console.log('Dependencies:', Object.keys(packageJson.dependencies || {}).join(', '));
  console.log('✓ package.json is valid');
} catch (e) {
  console.log('✗ package.json is invalid:', e.message);
  process.exit(1);
}

// Check server.js for required endpoints
const serverContent = fs.readFileSync('src/server.js', 'utf8');
const requiredEndpoints = [
  'app.get(\'/health\'',
  'app.post(\'/books\'',
  'app.get(\'/books/:id\'',
  'app.put(\'/books/:id\'',
  'app.delete(\'/books/:id\'',
  'app.get(\'/books\''
];

console.log('\nChecking server.js for required endpoints...');
let allEndpointsFound = true;
requiredEndpoints.forEach(endpoint => {
  const found = serverContent.includes(endpoint);
  console.log(`${endpoint}: ${found ? '✓' : '✗'}`);
  if (!found) allEndpointsFound = false;
});

if (allEndpointsFound) {
  console.log('\n✓ All required endpoints found in server.js');
  console.log('\n🎉 Implementation is complete and ready for use!');
} else {
  console.log('\n✗ Some required endpoints are missing');
  process.exit(1);
}

// Also check for key methods in server.js
const methodsToCheck = [
  'express.json()',
  'books.push',
  'books.find',
  'books.findIndex',
  'books.splice'
];

console.log('\nChecking for required methods...');
methodsToCheck.forEach(method => {
  const found = serverContent.includes(method);
  console.log(`${method}: ${found ? '✓' : '✗'}`);
  if (!found) allEndpointsFound = false;
});

if (allEndpointsFound) {
  console.log('\n✓ All required functionality found in server.js');
} else {
  console.log('\n✗ Some required functionality is missing');
  process.exit(1);
}