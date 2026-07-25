import * as sqlite3 from 'sqlite3';

let db: sqlite3.Database | null = null;
let testDb: sqlite3.Database | null = null;

// Set a test database for testing
export function setTestDatabase(database: sqlite3.Database) {
  testDb = database;
}

export function getDatabase(): sqlite3.Database {
  if (testDb) {
    return testDb;
  }
  
  if (!db) {
    db = new sqlite3.Database('./books.db');
    db.serialize(() => {
      db!.run(`
        CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          author TEXT NOT NULL,
          year INTEGER,
          isbn TEXT
        )
      `);
    });
  }
  return db;
}

export function closeDatabase(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (testDb) {
      testDb.close((err) => {
        if (err) {
          reject(err);
        } else {
          testDb = null;
          resolve();
        }
      });
    } else if (db) {
      db.close((err) => {
        if (err) {
          reject(err);
        } else {
          db = null;
          resolve();
        }
      });
    } else {
      resolve();
    }
  });
}
