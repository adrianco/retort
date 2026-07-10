import db from '../database';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export function validateBookInput(body: any): string[] {
  const errors: string[] = [];

  if (!body || typeof body !== 'object') {
    return ['Request body must be a JSON object'];
  }

  const { title, author } = body;
  if (!title || typeof title !== 'string' || title.trim().length === 0) {
    errors.push('title is required and must be a non-empty string');
  }
  if (!author || typeof author !== 'string' || author.trim().length === 0) {
    errors.push('author is required and must be a non-empty string');
  }

  return errors;
}

const createBookStmt = db.prepare(
  'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
);

export function createBook(body: any): Promise<Book> {
  return new Promise((resolve, reject) => {
    try {
      const result = createBookStmt.run(
        body.title.trim(),
        body.author.trim(),
        body.year || null,
        body.isbn ? body.isbn.trim() : null
      );
      const book = getBookByIdSync(result.lastInsertRowid as number);
      if (!book) {
        reject(new Error('Failed to create book'));
      } else {
        resolve(book);
      }
    } catch (err) {
      if (err instanceof Error && err.message.includes('UNIQUE constraint')) {
        reject(new Error('ISBN already exists'));
      } else {
        reject(err);
      }
    }
  });
}

const getBooksStmt = db.prepare(
  'SELECT * FROM books'
);

const getBooksByAuthorStmt = db.prepare(
  'SELECT * FROM books WHERE author = ?'
);

export function getBooks(author?: string): Promise<Book[]> {
  try {
    if (author) {
      return Promise.resolve(getBooksByAuthorStmt.all(author) as Book[]);
    }
    return Promise.resolve(getBooksStmt.all() as Book[]);
  } catch (err) {
    return Promise.reject(err);
  }
}

export function getBookByIdSync(id: number): Book | null {
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  return (stmt.get(id) as Book) || null;
}

export function getBookById(id: number): Promise<Book | null> {
  return Promise.resolve(getBookByIdSync(id));
}

const updateStmt = db.prepare(
  'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
);

export function updateBook(id: number, body: any): Promise<Book | null> {
  return new Promise((resolve, reject) => {
    try {
      updateStmt.run(
        body.title.trim(),
        body.author.trim(),
        body.year || null,
        body.isbn ? body.isbn.trim() : null,
        id
      );
      const book = getBookByIdSync(id);
      if (!book) {
        resolve(null);
      } else {
        resolve(book);
      }
    } catch (err) {
      if (err instanceof Error && err.message.includes('UNIQUE constraint')) {
        reject(new Error('ISBN already exists'));
      } else {
        reject(err);
      }
    }
  });
}

const deleteStmt = db.prepare('DELETE FROM books WHERE id = ?');

export function deleteBook(id: number): Promise<boolean> {
  const result = deleteStmt.run(id);
  return Promise.resolve(result.changes > 0);
}
