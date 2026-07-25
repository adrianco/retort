import { Router } from 'express';
import { getAllBooksHandler, getBookHandler, createBookHandler, updateBookHandler, deleteBookHandler } from '../controllers/books';
import { validateBookInput } from '../middleware/validation';

const router = Router();

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Book routes
router.get('/books', getAllBooksHandler);
router.get('/books/:id', getBookHandler);
router.post('/books', validateBookInput, createBookHandler);
router.put('/books/:id', validateBookInput, updateBookHandler);
router.delete('/books/:id', deleteBookHandler);

export default router;
