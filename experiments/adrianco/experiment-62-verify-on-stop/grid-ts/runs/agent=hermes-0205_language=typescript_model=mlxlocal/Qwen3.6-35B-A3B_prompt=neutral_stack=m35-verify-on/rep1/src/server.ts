import Database from 'better-sqlite3';
import path from 'path';
import { setDb } from './app';

const db = new Database(path.join(__dirname, '..', 'books.db'));
db.pragma('journal_mode = WAL');
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )
`);

setDb(db);

const PORT = process.env.PORT || 3000;
const { app } = require('./app');

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
