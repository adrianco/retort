import express, { Application, Request, Response } from 'express';
import { router } from './routes';
import { closeDatabase } from './db';

export const app: Application = express();
const PORT = parseInt(process.env.PORT || '3000', 10);

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.use('/', router);

// Only start server if run directly (not imported for tests)
if (process.env.NODE_ENV !== 'test') {
  const server = app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });

  // Graceful shutdown
  process.on('SIGINT', () => {
    console.log('Shutting down...');
    closeDatabase();
    server.close(() => {
      process.exit(0);
    });
  });

  process.on('SIGTERM', () => {
    console.log('Shutting down...');
    closeDatabase();
    server.close(() => {
      process.exit(0);
    });
  });
}

export default app;
