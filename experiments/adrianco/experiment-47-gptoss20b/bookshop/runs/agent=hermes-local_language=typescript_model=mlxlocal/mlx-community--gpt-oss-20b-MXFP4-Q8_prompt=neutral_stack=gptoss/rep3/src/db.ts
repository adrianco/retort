import sqlite3 = require('sqlite3');
import path from 'path';
import { promisify } from 'util';

const dbPath = path.join(__dirname, '..', 'data', 'books.db');
const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READWRITE | sqlite3.OPEN_CREATE);

const run = promisify(db.run.bind(db));
const get = promisify(db.get.bind(db));
const all = promisify(db.all.bind(db));

async function init() {
  await run(`CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)`);
}

export { init, run, get, all };
