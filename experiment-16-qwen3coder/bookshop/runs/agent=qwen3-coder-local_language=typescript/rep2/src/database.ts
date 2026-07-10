import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

// Open a connection to the SQLite database
export async function getDb() {
  return open({
    filename: './books.db',
    driver: sqlite3.Database
  });
}

// Initialize the database with the books table
export async function initDb() {
  const db = await getDb();
  
  await db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )
  `);
  
  return db;
}