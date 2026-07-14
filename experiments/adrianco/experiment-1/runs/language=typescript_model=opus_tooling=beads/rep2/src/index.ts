import { createApp } from './app';
import { createDb } from './db';

const port = Number(process.env.PORT) || 3000;
const dbPath = process.env.DB_PATH || 'books.db';

const db = createDb(dbPath);
const app = createApp(db);

app.listen(port, () => {
  console.log(`Book API listening on port ${port}`);
});
