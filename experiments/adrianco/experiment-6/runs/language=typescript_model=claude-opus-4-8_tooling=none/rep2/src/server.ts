import { createApp } from './app';
import { createDb } from './db';

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const DB_FILE = process.env.DB_FILE ?? 'books.db';

const db = createDb(DB_FILE);
const app = createApp(db);

app.listen(PORT, () => {
  console.log(`Book Collection API listening on http://localhost:${PORT}`);
});
