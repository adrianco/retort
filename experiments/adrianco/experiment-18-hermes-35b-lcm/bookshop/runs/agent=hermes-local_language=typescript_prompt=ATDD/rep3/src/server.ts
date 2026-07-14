import express, { Request, Response, Router } from 'express';
import Database from 'better-sqlite3';

interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
}

interface CreateBookDto {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

interface UpdateBookDto {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

/**
 * Create a fresh in-memory database with the books table.
 */
function createDatabase(): Database.Database {
  const db = new Database(':memory:');
  db.exec(`
    CREATE TABLE books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER NOT NULL,
      isbn TEXT NOT NULL UNIQUE
    )
  `);
  return db;
}

/**
 * Validate book data. Returns { error: string } on failure or { book: Book } on success.
 */
type ValidationResult = { error: string } | { book: Book };

function validateBook(data: CreateBookDto | UpdateBookDto): ValidationResult {
  if (!data.title || data.title.trim() === '') {
    return { error: 'Title is required' };
  }
  if (!data.author || data.author.trim() === '') {
    return { error: 'Author is required' };
  }

  const book: Book = {
    id: 0,
    title: data.title.trim(),
    author: data.author.trim(),
    year: data.year || new Date().getFullYear(),
    isbn: data.isbn || '',
  };

  return { book };
}

/**
 * Create an Express router with all book-related routes.
 */
function createBookRouter(db: Database.Database): Router {
  const router = Router();

  // POST /books - Create a new book
  router.post('/', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body;
    const result = validateBook({ title, author, year, isbn });

    if ('error' in result) {
      res.status(400).json({ error: result.error });
      return;
    }

    const book = result.book;

    try {
      const stmt = db.prepare(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
      );
      const runResult = stmt.run(book.title, book.author, book.year, book.isbn);
      const created: Book = {
        id: Number(runResult.lastInsertRowid),
        title: book.title,
        author: book.author,
        year: book.year,
        isbn: book.isbn,
      };
      res.status(201).json(created);
    } catch (e) {
      res.status(400).json({ error: 'Duplicate ISBN or database error' });
    }
  });

  // GET /books - List all books, optionally filtered by author
  router.get('/', (req: Request, res: Response) => {
    const { author } = req.query;
    let books: Book[];

    if (author && typeof author === 'string') {
      const stmt = db.prepare('SELECT * FROM books WHERE author = ?');
      books = stmt.all(author) as Book[];
    } else {
      const stmt = db.prepare('SELECT * FROM books');
      books = stmt.all() as Book[];
    }

    res.json(books);
  });

  // GET /books/:id - Get a single book by ID
  router.get('/:id', (req: Request, res: Response) => {
    const { id } = req.params;
    const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
    const row = stmt.get(Number(id)) as Book | undefined;

    if (!row) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.json(row);
  });

  // PUT /books/:id - Update a book
  router.put('/:id', (req: Request, res: Response) => {
    const { id } = req.params;
    const { title, author, year, isbn } = req.body;

    // Check if the book exists first
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(id)) as Book | undefined;
    if (!existing) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    // Validate - require title and author on update
    const result = validateBook({ title, author, year, isbn });
    if ('error' in result) {
      res.status(400).json({ error: result.error });
      return;
    }

    const updatedBook = result.book;

    try {
      const stmt = db.prepare(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
      );
      stmt.run(
        updatedBook.title,
        updatedBook.author,
        updatedBook.year,
        isbn || existing.isbn,
        Number(id)
      );
      const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(id)) as Book;
      res.json(updated);
    } catch (e) {
      res.status(400).json({ error: 'Could not update book' });
    }
  });

  // DELETE /books/:id - Delete a book
  router.delete('/:id', (req: Request, res: Response) => {
    const { id } = req.params;
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(id)) as Book | undefined;

    if (!existing) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    db.prepare('DELETE FROM books WHERE id = ?').run(Number(id));
    res.json(existing);
  });

  return router;
}

/**
 * Create the full Express application with health check and book routes.
 * When no database is provided, a fresh in-memory database is created.
 * This is the main export used by tests and the production server.
 */
export function createApp(db?: Database.Database): express.Application {
  const database = db || createDatabase();
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  // Book routes
  const router = createBookRouter(database);
  app.use('/books', router);

  return app;
}

/**
 * Initialize the SQLite database at a given path with the books table.
 */
export function initializeDatabase(dbPath?: string): { db: Database.Database } {
  const db = new Database(dbPath || ':memory:');
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER NOT NULL,
      isbn TEXT NOT NULL UNIQUE
    )
  `);

  return { db };
}

/**
 * Create an Express router with all book-related routes.
 */
export function getRouter(db: Database.Database): Router {
  return createBookRouter(db);
}

// If running directly, start the server
if (require.main === module) {
  const { db } = initializeDatabase();
  const app = createApp(db);
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => {
    console.log(`Book Collection API running on port ${PORT}`);
  });
}
