import { Router } from 'express';
import * as bookController from '../controllers/bookController';
import { validateBookInput, validateBookUpdateInput } from '../middleware/validation';

const router = Router();

router.post('/books', validateBookInput, bookController.createBook);
router.get('/books', bookController.getBooks);
router.get('/books/:id', bookController.getBookById);
router.put('/books/:id', validateBookUpdateInput, bookController.updateBook);
router.delete('/books/:id', bookController.deleteBook);

export default router;
