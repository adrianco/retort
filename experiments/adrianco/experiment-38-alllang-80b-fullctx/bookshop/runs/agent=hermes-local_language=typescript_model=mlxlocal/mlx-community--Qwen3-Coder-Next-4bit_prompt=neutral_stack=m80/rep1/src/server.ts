import express, { Application, Request, Response, NextFunction } from 'express';
import { BookController } from './controllers/BookController';
import { HealthController } from './controllers/HealthController';
import { DatabaseService } from './database';
import { BookService } from './services/BookService';

const PORT = process.env.PORT || 3000;

let app: Application;

function createApp(): Application {
  app = express();
  
  // Middleware
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // Create services
  const database = new DatabaseService('./books.db');
  const bookService = new BookService(database);
  const bookController = new BookController(bookService);
  const healthController = new HealthController();

  // Routes
  app.use('/books', bookController.getRouter());
  app.use('/health', healthController.getRouter());

  // Error handling middleware
  app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    console.error('Error:', err.message);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}

function startServer() {
  const app = createApp();
  
  // Start server
  app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });

  // Graceful shutdown
  process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down gracefully...');
    process.exit(0);
  });
}

// Start the server when this file is run directly
if (require.main === module) {
  startServer();
}

export { app, createApp };
