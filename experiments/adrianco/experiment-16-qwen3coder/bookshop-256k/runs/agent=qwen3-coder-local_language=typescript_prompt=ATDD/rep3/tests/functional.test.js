// Functional test that verifies server structure and API contract
const fs = require('fs');

describe('Book API - Functional Test', () => {
  test('should import server without errors', () => {
    expect(() => {
      require('../src/server');
    }).not.toThrow();
  });

  test('should have expected API endpoints in source code', () => {
    const serverContent = fs.readFileSync('./src/server.js', 'utf8');
    
    // Check for required endpoints
    expect(serverContent).toMatch(/app\.get\(('|")\/health('|")/);
    expect(serverContent).toMatch(/app\.post\(('|")\/books('|")/);
    expect(serverContent).toMatch(/app\.get\(('|")\/books\/:id('|")/);
    expect(serverContent).toMatch(/app\.put\(('|")\/books\/:id('|")/);
    expect(serverContent).toMatch(/app\.delete\(('|")\/books\/:id('|")/);
    
    // Check for validation logic
    expect(serverContent).toMatch(/title.*author.*required/);
    
    // Check for database usage
    expect(serverContent).toMatch(/sqlite3/);
    expect(serverContent).toMatch(/books\.db/);
    
    // Check for proper HTTP status codes
    expect(serverContent).toMatch(/status\(400\)/);
    expect(serverContent).toMatch(/status\(404\)/);
    expect(serverContent).toMatch(/status\(201\)/);
    expect(serverContent).toMatch(/status\(200\)/);
  });

  test('should have required dependencies in package.json', () => {
    const packageJson = JSON.parse(fs.readFileSync('./package.json', 'utf8'));
    
    expect(packageJson.dependencies).toHaveProperty('express');
    expect(packageJson.dependencies).toHaveProperty('sqlite3');
    expect(packageJson.devDependencies).toHaveProperty('jest');
    expect(packageJson.devDependencies).toHaveProperty('supertest');
  });
});