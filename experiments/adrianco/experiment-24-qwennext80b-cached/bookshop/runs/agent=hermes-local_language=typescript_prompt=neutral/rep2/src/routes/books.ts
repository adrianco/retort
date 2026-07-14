import { Router } from 'express';
import { BookController } from '../controllers/BookController';
import { validateBookCreate, validateBookUpdate } from '../middleware/validation';

const router = Router();

router.get('/', BookController.getAll);
router.get('/:id', BookController.getById);
router.post('/', validateBookCreate, BookController.create);
router.put('/:id', validateBookUpdate, BookController.update);
router.delete('/:id', BookController.delete);

export default router;
