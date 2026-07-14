import { Request, Response, NextFunction } from 'express';
import { validateBookInput as validateBookInputModel, validateBookUpdate as validateBookUpdateModel } from '../models/Book';

export const validateBookCreate = (req: Request, res: Response, next: NextFunction): void => {
  const { valid, errors } = validateBookInputModel(req.body);
  if (!valid) {
    res.status(400).json({ error: 'Validation failed', details: errors });
    return;
  }
  next();
};

export const validateBookUpdate = (req: Request, res: Response, next: NextFunction): void => {
  const { valid, errors } = validateBookUpdateModel(req.body);
  if (!valid) {
    res.status(400).json({ error: 'Validation failed', details: errors });
    return;
  }
  next();
};
