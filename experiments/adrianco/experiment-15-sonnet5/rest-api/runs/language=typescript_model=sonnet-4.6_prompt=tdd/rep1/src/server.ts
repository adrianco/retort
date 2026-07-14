import Database from 'better-sqlite3';
import { buildApp } from './app';

const db = new Database(process.env.DB_PATH ?? 'books.db');
const app = buildApp(db);
const port = Number(process.env.PORT ?? 3000);

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
