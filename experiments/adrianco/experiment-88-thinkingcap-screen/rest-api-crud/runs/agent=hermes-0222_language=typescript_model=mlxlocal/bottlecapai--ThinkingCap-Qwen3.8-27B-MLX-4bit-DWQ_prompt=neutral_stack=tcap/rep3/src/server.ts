import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createApp } from './app.js';
import { openDb } from './db.js';

const here = dirname(fileURLToPath(import.meta.url));
const dbPath = process.env.DATABASE_PATH ?? join(here, '..', 'books.db');
const port = Number(process.env.PORT ?? 8000);

const app = createApp(openDb(dbPath));

app.listen(port, () => {
  console.log(`Book API listening on http://localhost:${port} (db: ${dbPath})`);
});
