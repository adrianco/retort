import { createApp } from './app';
import { BookStore } from './db';

const PORT = Number(process.env.PORT ?? 3000);
const DB_PATH = process.env.DB_PATH ?? 'books.db';

const store = new BookStore(DB_PATH);
const app = createApp(store);

const server = app.listen(PORT, () => {
  console.log(`Book API listening on port ${PORT}`);
});

function shutdown(): void {
  server.close(() => {
    store.close();
    process.exit(0);
  });
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
