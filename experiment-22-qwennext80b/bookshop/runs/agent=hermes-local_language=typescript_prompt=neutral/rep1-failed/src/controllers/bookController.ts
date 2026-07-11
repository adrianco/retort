import { Request, Response } from 'express';
import { BookModel } from '../models/BookModel';

const bookModel = new BookModel();

export const getBooks = async (req: Request, res: Response): Promise<Response> => {
  try {
    const author = req.query.author as string | undefined;
    const books = await bookModel.findAll(author);
    return res.json(books);
  } catch (error) {
    console.error('Error fetching books:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
};

export const getBookById = async (req: Request, res: Response): Promise<Response> => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const book = await bookModel.findById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }

    return res.json(book);
  } catch (error) {
    console.error('Error fetching book by ID:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
};

export const createBook = async (req: Request, res: Response): Promise<Response> => {
  try {
    const book = req.body;
    const newBook = await bookModel.create(book);
    return res.status(201).json(newBook);
  } catch (error) {
    console.error('Error creating book:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
};

export const updateBook = async (req: Request, res: Response): Promise<Response> => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const book = await bookModel.update(id, req.body);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }

    return res.json(book);
  } catch (error) {
    console.error('Error updating book:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
};

export const deleteBook = async (req: Request, res: Response): Promise<Response> => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const deleted = await bookModel.delete(id);
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }

    return res.status(204).send();
  } catch (error) {
    console.error('Error deleting book:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
};
