import { createApp } from './app.js';
import { BookStore } from './db.js';

const port = Number(process.env['PORT'] ?? 3000);
const dbFile = process.env['DATABASE_FILE'] ?? 'books.db';

const store = new BookStore(dbFile);
const server = createApp(store).listen(port, () => {
  console.log(`books API listening on http://localhost:${port} (db: ${dbFile})`);
});

function shutdown(signal: string): void {
  console.log(`\n${signal} received, shutting down`);
  server.close(() => {
    store.close();
    process.exit(0);
  });
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
