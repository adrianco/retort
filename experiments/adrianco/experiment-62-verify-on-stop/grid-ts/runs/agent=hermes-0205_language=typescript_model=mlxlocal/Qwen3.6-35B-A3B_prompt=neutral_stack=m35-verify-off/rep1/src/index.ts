import express from 'express';
import {
  getAllBooks,
  getBookById,
  createBook,
  updateBook,
  deleteBook,
  closeDb,
  Book,
} from './database';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// Health check endpoint
app.get('/health', (_req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// POST /books — Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;

  // Input validation: title and author are required
  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({
      error: 'Validation failed',
      message: 'Title is required and must be a non-empty string',
    });
  }

  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({
      error: 'Validation failed',
      message: 'Author is required and must be a non-empty string',
    });
  }

  // Validate year if provided
  if (year !== undefined && year !== null) {
    const yearNum = Number(year);
    if (!Number.isInteger(yearNum) || yearNum < 0 || yearNum > new Date().getFullYear() + 1) {
      return res.status(400).json({
        error: 'Validation failed',
        message: 'Year must be a valid integer between 0 and current year + 1',
      });
    }
  }

  const book = createBook(
    title.trim(),
    author.trim(),
    year !== undefined && year !== null ? Number(year) : null,
    isbn !== undefined && isbn !== null ? String(isbn) : null,
  );

  res.status(201).json(book);
});

// GET /books — List all books with optional author filter
app.get('/books', (req, res) => {
  const { author } = req.query;

  if (author !== undefined && typeof author !== 'string') {
    return res.status(400).json({
      error: 'Validation failed',
      message: 'Author filter must be a string',
    });
  }

  const books = getAllBooks(author as string | undefined);
  res.status(200).json(books);
});

// GET /books/:id — Get a single book by ID
app.get('/books/:id', (req, res) => {
  const id = Number(req.params.id);

  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({
      error: 'Validation failed',
      message: 'Book ID must be a positive integer',
    });
  }

  const book = getBookById(id);

  if (!book) {
    return res.status(404).json({
      error: 'Not found',
      message: `Book with ID ${id} not found`,
    });
  }

  res.status(200).json(book);
});

// PUT /books/:id — Update a book
app.put('/books/:id', (req, res) => {
  const id = Number(req.params.id);

  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({
      error: 'Validation failed',
      message: 'Book ID must be a positive integer',
    });
  }

  const existing = getBookById(id);
  if (!existing) {
    return res.status(404).json({
      error: 'Not found',
      message: `Book with ID ${id} not found`,
    });
  }

  const { title, author, year, isbn } = req.body;

  // Validate title if provided
  if (title !== undefined) {
    if (typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({
        error: 'Validation failed',
        message: 'Title must be a non-empty string',
      });
    }
  }

  // Validate author if provided
  if (author !== undefined) {
    if (typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({
        error: 'Validation failed',
        message: 'Author must be a non-empty string',
      });
    }
  }

  // Validate year if provided
  if (year !== undefined && year !== null) {
    const yearNum = Number(year);
    if (!Number.isInteger(yearNum) || yearNum < 0 || yearNum > new Date().getFullYear() + 1) {
      return res.status(400).json({
        error: 'Validation failed',
        message: 'Year must be a valid integer between 0 and current year + 1',
      });
    }
  }

  const book = updateBook(
    id,
    title !== undefined ? title.trim() : undefined,
    author !== undefined ? author.trim() : undefined,
    year !== undefined && year !== null ? Number(year) : undefined,
    isbn !== undefined && isbn !== null ? String(isbn) : undefined,
  );

  res.status(200).json(book);
});

// DELETE /books/:id — Delete a book
app.delete('/books/:id', (req, res) => {
  const id = Number(req.params.id);

  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({
      error: 'Validation failed',
      message: 'Book ID must be a positive integer',
    });
  }

  const existing = getBookById(id);
  if (!existing) {
    return res.status(404).json({
      error: 'Not found',
      message: `Book with ID ${id} not found`,
    });
  }

  deleteBook(id);
  res.status(204).send();
});

let server: ReturnType<typeof app.listen>;

function startServer(): ReturnType<typeof app.listen> {
  server = app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
  return server;
}

function stopServer(): void {
  if (server) {
    server.close();
  }
  closeDb();
}

export { app, startServer, stopServer };

// Start server when run directly
if (require.main === module) {
  startServer();
}
