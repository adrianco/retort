import { createApp } from './app';
import { openDatabase } from './db';

const port = Number(process.env.PORT ?? 8000);
const dbPath = process.env.DB_PATH ?? 'books.db';

const app = createApp(openDatabase(dbPath));

app.listen(port, () => {
  console.log(`Book API listening on http://localhost:${port} (db: ${dbPath})`);
});
