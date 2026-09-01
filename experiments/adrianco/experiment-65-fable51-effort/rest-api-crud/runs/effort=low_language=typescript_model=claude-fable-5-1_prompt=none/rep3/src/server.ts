import { createApp } from './app.js';
import { BookRepository } from './db.js';

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? 'books.db';

const repo = new BookRepository(dbPath);
const app = createApp(repo);

const server = app.listen(port, () => {
  console.log(`books-api listening on http://localhost:${port} (db: ${dbPath})`);
});

for (const sig of ['SIGINT', 'SIGTERM'] as const) {
  process.on(sig, () => {
    server.close(() => {
      repo.close();
      process.exit(0);
    });
  });
}
