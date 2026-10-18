import { DatabaseSync } from 'node:sqlite';
import { createApp } from './app.ts';

const databasePath = process.env.DATABASE_PATH ?? './books.sqlite';
const port = Number(process.env.PORT ?? 3000);
const db = new DatabaseSync(databasePath);
const server = createApp(db).listen(port, () => {
  console.log(`Book API listening on port ${port}`);
});

function shutdown() {
  server.close(() => {
    db.close();
    process.exit(0);
  });
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
