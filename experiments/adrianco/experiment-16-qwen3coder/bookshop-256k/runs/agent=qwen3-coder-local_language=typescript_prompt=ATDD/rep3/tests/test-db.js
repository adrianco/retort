const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Create an in-memory test database
const createTestDB = () => {
  const db = new sqlite3.Database(':memory:');
  db.serialize(() => {
    db.run(`CREATE TABLE books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )`);
  });
  return db;
};

// Close test database
const closeTestDB = (db) => {
  db.close();
};

module.exports = {
  createTestDB,
  closeTestDB
};