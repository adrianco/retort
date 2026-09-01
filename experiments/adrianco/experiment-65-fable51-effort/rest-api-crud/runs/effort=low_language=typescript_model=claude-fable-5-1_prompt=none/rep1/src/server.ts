import { createApp } from './app.js';
import { BookRepository } from './db.js';

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? 'books.db';

const repo = new BookRepository(dbPath);
const app = createApp(repo);

app.listen(port, () => {
  console.log(`Book API listening on http://localhost:${port} (db: ${dbPath})`);
});
