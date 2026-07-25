import * as sqlite3 from 'sqlite3';
import { open } from 'sqlite';

export async function getDb(dbPath: string = './books.db') {
  const db = await open({
    filename: dbPath,
    driver: sqlite3.Database
  });
  await db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    );
  `);
  return db;
}
