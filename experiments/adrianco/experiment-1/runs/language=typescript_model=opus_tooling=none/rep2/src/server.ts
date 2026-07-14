import { createApp } from './app';
import { createDb } from './db';

const dbFile = process.env.DB_FILE ?? 'books.db';
const port = Number(process.env.PORT ?? 3000);

const db = createDb(dbFile);
const app = createApp(db);

app.listen(port, () => {
  console.log(`Book API listening on http://localhost:${port}`);
});
