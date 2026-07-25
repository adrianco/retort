import sqlite3 from 'sqlite3';

export const db = new sqlite3.Database(':memory:', (err) => {
  if (err) console.error(err);
});

export function initDb(): Promise<void> {
  return new Promise((resolve, reject) => {
    db.run(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      );
    `, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

export function runAsync(sql: string, params?: any[]): Promise<any> {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
}

export function getAsync<T = any>(sql: string, params?: any[]): Promise<T | undefined> {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) reject(err);
      else resolve(row as T | undefined);
    });
  });
}

export function allAsync<T = any>(sql: string, params?: any[]): Promise<T[]> {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows as T[]);
    });
  });
}
