import { Request, Response, NextFunction } from 'express';
import { BookInput } from '../types';

export function validateBookInput(req: Request, res: Response, next: NextFunction): Response | void {
  const { title, author, year, isbn } = req.body;
  
  if (!title || !title.trim()) {
    return res.status(400).json({ error: 'Title is required' });
  }
  
  if (!author || !author.trim()) {
    return res.status(400).json({ error: 'Author is required' });
  }
  
  if (year !== undefined && year !== null) {
    const yearNum = Number(year);
    if (isNaN(yearNum) || yearNum < 0 || yearNum > 9999) {
      return res.status(400).json({ error: 'Invalid year' });
    }
  }
  
  next();
}
