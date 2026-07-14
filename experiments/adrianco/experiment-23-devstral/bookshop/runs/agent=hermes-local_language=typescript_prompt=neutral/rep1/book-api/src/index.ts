import express from 'express';
import bodyParser from 'body-parser';
import {
  initializeDatabase,
  getAllBooks,
  getBookById,
  createBook,
  updateBook,
  deleteBook
} from './database';

const app = express();
const PORT = process.env.PORT || 3000;

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

initializeDatabase().then(() => {
  app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });
}).catch(err => {
  console.error('Failed to initialize database:', err);
});
