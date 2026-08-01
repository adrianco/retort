import { createApp } from './app.ts';

const port = Number(process.env.PORT ?? 3000);
const server = createApp({ databasePath: process.env.DATABASE_PATH ?? 'books.db' });

server.listen(port, () => {
  console.log(`Book API listening on http://localhost:${port}`);
});
