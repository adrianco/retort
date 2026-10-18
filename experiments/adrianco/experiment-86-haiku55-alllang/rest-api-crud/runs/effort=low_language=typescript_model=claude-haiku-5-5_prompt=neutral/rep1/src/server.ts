import { BookRepository } from './repository';
import { createServer } from './app';

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DATABASE_PATH ?? 'books.db';

const repo = new BookRepository(dbPath);
const server = createServer(repo);

server.listen(port, () => {
  console.log(`Book API listening on http://localhost:${port} (db: ${dbPath})`);
});

const shutdown = () => {
  server.close(() => {
    repo.close();
    process.exit(0);
  });
};
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
