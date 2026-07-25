import { Request, Response } from 'express';
import { BookInput } from '../types';
import { getAllBooks, getBookById, createBook, updateBook, deleteBook } from '../models/book';

export async function getAllBooksHandler(req: Request, res: Response): Promise<void> {
  try {
    const author = req.query.author as string | undefined;
    const books = await getAllBooks(author);
    res.json(books);
  } catch (error) {
    res.status(500).json({ error: 'Failed to retrieve books' });
  }
}

export async function getBookHandler(req: Request, res: Response): Promise<void> {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }
    
    const book = await getBookById(id);
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    
    res.json(book);
  } catch (error) {
    res.status(500).json({ error: 'Failed to retrieve book' });
  }
}

export async function createBookHandler(req: Request, res: Response): Promise<void> {
  try {
    const book: BookInput = req.body;
    const newBook = await createBook(book);
    res.status(201).json(newBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to create book' });
  }
}

export async function updateBookHandler(req: Request, res: Response): Promise<void> {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }
    
    const book: BookInput = req.body;
    const updatedBook = await updateBook(id, book);
    
    if (!updatedBook) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    
    res.json(updatedBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update book' });
  }
}

export async function deleteBookHandler(req: Request, res: Response): Promise<void> {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }
    
    const deleted = await deleteBook(id);
    if (!deleted) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    
    res.status(204).send();
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
}
