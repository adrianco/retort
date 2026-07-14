import { createApp } from './app';

const port = Number(process.env.PORT) || 3000;
const dbFile = process.env.DB_FILE || 'books.sqlite';

const { app } = createApp({ dbFile });

app.listen(port, () => {
  console.log(`book-collection-api listening on port ${port} (db: ${dbFile})`);
});
