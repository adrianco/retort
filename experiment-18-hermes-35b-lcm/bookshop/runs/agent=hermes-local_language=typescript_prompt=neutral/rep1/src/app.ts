import express from 'express';
import db from './database';
import {
  validateBookInput,
  createBook,
  getBooks,
  getBookById,
  updateBook,
  deleteBook
} from './routes/books';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// Health check
app.get('/health', (_req: any, res: any) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// POST /books
app.post('/books', (req: any, res: any, next: any) => {
  const errors = validateBookInput(req.body);
  if (errors.length > 0) {
    return res.status(400).json({ errors });
  }
  createBook(req.body)
    .then((book: any) => res.status(201).json(book))
    .catch(next);
});

// GET /books
app.get('/books', (req: any, res: any, next: any) => {
  const authorParam = req.query.author;
  const author = typeof authorParam === 'string' ? authorParam : undefined;
  getBooks(author)
    .then((books: any) => res.status(200).json(books))
    .catch(next);
});

// GET /books/:id
app.get('/books/:id', (req: any, res: any, next: any) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ errors: ['Invalid book ID'] });
  }
  getBookById(id)
    .then((book: any) => {
      if (!book) return res.status(404).json({ errors: ['Book not found'] });
      res.status(200).json(book);
    })
    .catch(next);
});

// PUT /books/:id
app.put('/books/:id', (req: any, res: any, next: any) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ errors: ['Invalid book ID'] });
  }
  const errors = validateBookInput(req.body);
  if (errors.length > 0) {
    return res.status(400).json({ errors });
  }
  updateBook(id, req.body)
    .then((book: any) => {
      if (!book) return res.status(404).json({ errors: ['Book not found'] });
      res.status(200).json(book);
    })
    .catch(next);
});

// DELETE /books/:id
app.delete('/books/:id', (req: any, res: any, next: any) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ errors: ['Invalid book ID'] });
  }
  deleteBook(id)
    .then((deleted: boolean) => {
      if (!deleted) return res.status(404).json({ errors: ['Book not found'] });
      res.status(204).send();
    })
    .catch(next);
});

// Error handling middleware
app.use((err: Error, _req: any, res: any, _next: any) => {
  console.error(err.stack);
  res.status(500).json({ errors: ['Internal server error'] });
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export default app;
