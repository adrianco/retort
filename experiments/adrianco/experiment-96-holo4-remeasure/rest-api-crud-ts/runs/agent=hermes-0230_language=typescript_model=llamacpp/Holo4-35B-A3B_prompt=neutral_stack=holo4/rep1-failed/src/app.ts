import express, { Request, Response } from 'express';
// @ts-ignore
import initSqlJs = require('sql.js');
import fs from 'fs';

let db: any = null;
const dbPromise = initSqlJs().then((SQL: any) => {
  const data = fs.existsSync('books.db') ? fs.readFileSync('books.db') : null;
  const instance = new SQL.Database(data);
  instance.run(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  db = instance;
  return instance;
});

// Save database to disk after each write
function saveDb() {
  if (!db) return;
  const data = db.export();
  fs.writeFileSync('books.db', Buffer.from(data));
}

const app = express();
app.use(express.json());

// POST /books — Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  db!.run('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)', [title, author, year || null, isbn || null]);
  saveDb();

  const result = db!.exec('SELECT * FROM books WHERE id = last_insert_rowid()');
  const row = result[0].values[0];
  res.status(201).json({ id: row[0], title: row[1], author: row[2], year: row[3], isbn: row[4] });
});

// GET /books — List all books (support ?author= filter)
app.get('/books', (req: Request, res: Response) => {
  const { author } = req.query;

  let results: { columns: string[]; values: any[][] }[];
  if (author) {
    const safeAuthor = String(author).replace(/'/g, "''");
    results = db!.exec(`SELECT * FROM books WHERE author = '${safeAuthor}'`);
  } else {
    results = db!.exec('SELECT * FROM books');
  }

  if (results.length === 0) {
    return res.json([]);
  }

  const columns = results[0].columns;
  const rows = results[0].values.map((row: number[]) => {
    const obj: Record<string, any> = {};
    columns.forEach((col: string, i: number) => {
      obj[col] = row[i];
    });
    return obj;
  });

  res.json(rows);
});

// GET /books/:id — Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const results = db!.exec(`SELECT * FROM books WHERE id = ${id}`);

  if (results.length === 0 || results[0].values.length === 0) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const columns = results[0].columns;
  const row = results[0].values[0];
  const book: Record<string, any> = {};
  columns.forEach((col: string, i: number) => {
    book[col] = row[i];
  });
  res.json(book);
});

// PUT /books/:id — Update a book
app.put('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const { title, author, year, isbn } = req.body;

  const results = db!.exec(`SELECT * FROM books WHERE id = ${id}`);
  if (results.length === 0 || results[0].values.length === 0) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const columns = results[0].columns;
  const row = results[0].values[0];
  const existing: Record<string, any> = {};
  columns.forEach((col: string, i: number) => {
    existing[col] = row[i];
  });

  const newTitle = title || existing.title;
  const newAuthor = author || existing.author;
  const newYear = year !== undefined ? year : existing.year;
  const newIsbn = isbn !== undefined ? isbn : existing.isbn;

  db!.run(`UPDATE books SET title = '${newTitle}', author = '${newAuthor}', year = ${newYear}, isbn = '${newIsbn}' WHERE id = ${id}`);
  saveDb();

  const updated = db!.exec(`SELECT * FROM books WHERE id = ${id}`)[0];
  const updatedColumns = updated.columns;
  const updatedRow = updated.values[0];
  const book: Record<string, any> = {};
  updatedColumns.forEach((col: string, i: number) => {
    book[col] = updatedRow[i];
  });
  res.json(book);
});

// DELETE /books/:id — Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const results = db!.exec(`SELECT * FROM books WHERE id = ${id}`);

  if (results.length === 0 || results[0].values.length === 0) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db!.run(`DELETE FROM books WHERE id = ${id}`);
  saveDb();
  res.status(204).send();
});

// GET /health — Health check
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok' });
});

const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

export { app, dbPromise };
