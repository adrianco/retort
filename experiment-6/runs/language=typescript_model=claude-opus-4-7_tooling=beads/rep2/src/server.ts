import { createApp } from './app';
import { BookStore } from './db';

const port = Number(process.env.PORT) || 3000;
const dbFile = process.env.DB_FILE || 'books.db';

const store = new BookStore(dbFile);
const app = createApp(store);

const server = app.listen(port, () => {
  console.log(`Books API listening on port ${port}`);
});

function shutdown(): void {
  console.log('Shutting down...');
  server.close(() => {
    store.close();
    process.exit(0);
  });
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
