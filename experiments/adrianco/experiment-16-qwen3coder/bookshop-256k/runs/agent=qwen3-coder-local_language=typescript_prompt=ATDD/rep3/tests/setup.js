const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

// Create a temporary database for testing
const createTestDatabase = () => {
  const testDbPath = path.join(__dirname, 'test.db');
  const db = new sqlite3.Database(testDbPath);
  
  db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )`);
  });
  
  return { db, path: testDbPath };
};

// Clean up test database
const cleanupTestDatabase = (testDbPath) => {
  try {
    fs.unlinkSync(testDbPath);
  } catch (err) {
    // Ignore if file doesn't exist
  }
};

module.exports = {
  createTestDatabase,
  cleanupTestDatabase
};