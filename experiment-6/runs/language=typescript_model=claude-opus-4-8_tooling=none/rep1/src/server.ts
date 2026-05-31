import { createApp } from './app';
import { createDb, BookRepository } from './db';

const PORT = Number(process.env.PORT) || 3000;
const DB_PATH = process.env.DB_PATH || 'books.db';

const db = createDb(DB_PATH);
const repo = new BookRepository(db);
const app = createApp(repo);

app.listen(PORT, () => {
  console.log(`Book Collection API listening on http://localhost:${PORT}`);
});
