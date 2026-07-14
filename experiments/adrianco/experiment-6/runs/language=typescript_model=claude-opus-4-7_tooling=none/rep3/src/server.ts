import { createApp } from './app';
import { createDb } from './db';

const port = Number(process.env.PORT) || 3000;
const dbFile = process.env.DB_FILE || 'books.db';

const db = createDb(dbFile);
const app = createApp(db);

app.listen(port, () => {
  console.log(`Books API listening on port ${port}`);
});
