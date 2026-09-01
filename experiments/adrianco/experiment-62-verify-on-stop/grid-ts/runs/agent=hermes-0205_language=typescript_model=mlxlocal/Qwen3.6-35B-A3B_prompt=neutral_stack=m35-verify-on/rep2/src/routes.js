const express = require('express');
const { createBook, getAllBooks, getBookById, updateBook, deleteBook } = require('./db');

const router = express.Router();

function validateCreateBook(body) {
  const errors = [];
  if (!body || typeof body !== 'object') {
    return [{ field: 'body', message: 'Request body must be a JSON object' }];
  }
  if (!body.title || typeof body.title !== 'string' || body.title.trim().length === 0) {
    errors.push({ field: 'title', message: 'Title is required and must be a non-empty string' });
  }
  if (!body.author || typeof body.author !== 'string' || body.author.trim().length === 0) {
    errors.push({ field: 'author', message: 'Author is required and must be a non-empty string' });
  }
  if (body.year === undefined || body.year === null) {
    errors.push({ field: 'year', message: 'Year is required' });
  } else if (typeof body.year !== 'number' || !Number.isInteger(body.year)) {
    errors.push({ field: 'year', message: 'Year must be an integer' });
  } else if (body.year < 0 || body.year > new Date().getFullYear() + 1) {
    errors.push({ field: 'year', message: 'Year must be a reasonable value' });
  }
  if (body.isbn === undefined || body.isbn === null) {
    errors.push({ field: 'isbn', message: 'ISBN is required' });
  } else if (typeof body.isbn !== 'string' || body.isbn.trim().length === 0) {
    errors.push({ field: 'isbn', message: 'ISBN must be a non-empty string' });
  }
  return errors;
}

function validateUpdateBook(body) {
  const errors = [];
  if (!body || typeof body !== 'object') {
    return [{ field: 'body', message: 'Request body must be a JSON object' }];
  }
  if (body.title !== undefined && (typeof body.title !== 'string' || body.title.trim().length === 0)) {
    errors.push({ field: 'title', message: 'Title must be a non-empty string' });
  }
  if (body.author !== undefined && (typeof body.author !== 'string' || body.author.trim().length === 0)) {
    errors.push({ field: 'author', message: 'Author must be a non-empty string' });
  }
  if (body.year !== undefined && (typeof body.year !== 'number' || !Number.isInteger(body.year))) {
    errors.push({ field: 'year', message: 'Year must be an integer' });
  }
  if (body.isbn !== undefined && (typeof body.isbn !== 'string' || body.isbn.trim().length === 0)) {
    errors.push({ field: 'isbn', message: 'ISBN must be a non-empty string' });
  }
  return errors;
}

router.post('/books', (req, res) => {
  const validationErrors = validateCreateBook(req.body);
  if (validationErrors.length > 0) {
    return res.status(400).json({ error: 'Validation failed', validation_errors: validationErrors });
  }

  const dto = {
    title: req.body.title.trim(),
    author: req.body.author.trim(),
    year: req.body.year,
    isbn: req.body.isbn.trim(),
  };

  try {
    const book = createBook(dto);
    return res.status(201).json(book);
  } catch (err) {
    if (err instanceof Error && err.message.includes('UNIQUE constraint')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    return res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/books', (req, res) => {
  const author = req.query.author;
  const books = getAllBooks(author);
  return res.status(200).json(books);
});

router.get('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const book = getBookById(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  return res.status(200).json(book);
});

router.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const validationErrors = validateUpdateBook(req.body);
  if (validationErrors.length > 0) {
    return res.status(400).json({ error: 'Validation failed', validation_errors: validationErrors });
  }

  const dto = {};
  if (req.body.title !== undefined) dto.title = req.body.title.trim();
  if (req.body.author !== undefined) dto.author = req.body.author.trim();
  if (req.body.year !== undefined) dto.year = req.body.year;
  if (req.body.isbn !== undefined) dto.isbn = req.body.isbn.trim();

  const book = updateBook(id, dto);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  return res.status(200).json(book);
});

router.delete('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const deleted = deleteBook(id);
  if (!deleted) {
    return res.status(404).json({ error: 'Book not found' });
  }
  return res.status(204).send();
});

module.exports = router;
