import express from 'express';
import Database from 'better-sqlite3';
import { createBooksRouter } from './books';

export function createApp(db: Database.Database) {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok' });
  });

  // Books routes
  app.use('/books', createBooksRouter(db));

  return app;
}
