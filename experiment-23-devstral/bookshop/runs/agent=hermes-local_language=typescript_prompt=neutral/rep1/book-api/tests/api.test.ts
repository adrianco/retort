import request from 'supertest';
import express from 'express';
import bodyParser from 'body-parser';
import { expect } from 'chai';
import {
  initializeDatabase,
  getAllBooks,
  getBookById,
  createBook,
  updateBook,
  deleteBook
} from '../src/database';

const app = express();
app.use(bodyParser.json());

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

app.get('/books', async (req, res) => {
  try {
    const author = req.query.author as string;
    const books = await getAllBooks(author);
    res.status(200).json(books);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid ID' });
    }
    
    const book = await getBookById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json(book);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.post('/books', async (req, res) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }
    
    const id = await createBook(title, author, year, isbn);
    const newBook = await getBookById(id);
    
    res.status(201).json(newBook);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.put('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid ID' });
    }
    
    const { title, author, year, isbn } = req.body;
    
    if (!title && !author && year === undefined && !isbn) {
      return res.status(400).json({ error: 'No fields to update' });
    }
    
    const book = await getBookById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    await updateBook(id, title, author, year, isbn);
    const updatedBook = await getBookById(id);
    
    res.status(200).json(updatedBook);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.delete('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid ID' });
    }
    
    const book = await getBookById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    await deleteBook(id);
    
    res.status(204).send();
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

describe('Book API', function () {
  this.timeout(5000);
  
  before(async () => {
    await initializeDatabase();
  });
  
  it('should return health check', async () => {
    const res = await request(app).get('/health');
    expect(res.status).to.equal(200);
    expect(res.body.status).to.equal('OK');
  });
  
  it('should create a book', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'API Test Book', author: 'API Test Author', year: 2023, isbn: '987-6543210987' });
    
    expect(res.status).to.equal(201);
    expect(res.body).to.have.property('id');
    expect(res.body.title).to.equal('API Test Book');
    expect(res.body.author).to.equal('API Test Author');
    expect(res.body.year).to.equal(2023);
    expect(res.body.isbn).to.equal('987-6543210987');
  });
  
  it('should return validation error for missing required fields', async () => {
    const res = await request(app)
      .post('/books')
      .send({ year: 2023 });
    
    expect(res.status).to.equal(400);
    expect(res.body.error).to.equal('Title and author are required');
  });
  
  it('should get all books', async () => {
    const res = await request(app).get('/books');
    expect(res.status).to.equal(200);
    expect(res.body).to.be.an('array').that.is.not.empty;
  });
  
  it('should filter books by author', async () => {
    await request(app)
      .post('/books')
      .send({ title: 'Filtered Book', author: 'Filtered Author' });
    
    const res = await request(app).get('/books').query({ author: 'API Test Author' });
    expect(res.status).to.equal(200);
    expect(res.body).to.have.lengthOf(1);
    expect(res.body[0].title).to.equal('API Test Book');
  });
  
  it('should get a book by ID', async () => {
    const res = await request(app).get('/books');
    const bookId = res.body[0].id;
    
    const bookRes = await request(app).get(`/books/${bookId}`);
    expect(bookRes.status).to.equal(200);
    expect(bookRes.body).to.have.property('id', bookId);
  });
  
  it('should return 404 for non-existent book', async () => {
    const res = await request(app).get('/books/99999');
    expect(res.status).to.equal(404);
    expect(res.body.error).to.equal('Book not found');
  });
  
  it('should update a book', async () => {
    const res = await request(app).get('/books');
    const bookId = res.body[0].id;
    
    const updateRes = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'Updated API Book' });
    
    expect(updateRes.status).to.equal(200);
    expect(updateRes.body.title).to.equal('Updated API Book');
  });
  
  it('should return validation error for invalid ID', async () => {
    const res = await request(app).put('/books/invalid').send({ title: 'Updated Book' });
    expect(res.status).to.equal(400);
    expect(res.body.error).to.equal('Invalid ID');
  });
  
  it('should delete a book', async () => {
    const res = await request(app).get('/books');
    const bookId = res.body[0].id;
    
    const deleteRes = await request(app).delete(`/books/${bookId}`);
    expect(deleteRes.status).to.equal(204);
    
    const bookRes = await request(app).get(`/books/${bookId}`);
    expect(bookRes.status).to.equal(404);
  });
});
