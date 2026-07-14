const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Initialize database
const dbPath = path.join(__dirname, '../books.db');
const db = new sqlite3.Database(dbPath);

// Create books table if it doesn't exist
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
  )`);
});

// Export database for testing
module.exports = {
  db,
  dbPath
};