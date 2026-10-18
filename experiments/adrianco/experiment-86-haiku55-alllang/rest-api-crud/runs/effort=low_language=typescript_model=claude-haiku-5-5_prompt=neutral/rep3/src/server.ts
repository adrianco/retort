import { BookRepository } from './db.js';
import { createApp } from './app.js';

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DATABASE_PATH ?? 'data/books.db';

if (dbPath !== ':memory:') {
  const { mkdirSync } = await import('node:fs');
  const { dirname } = await import('node:path');
  mkdirSync(dirname(dbPath), { recursive: true });
}

const repo = new BookRepository(dbPath);
const server = createApp(repo);

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
