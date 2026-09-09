import { createApp } from './app.js';
import { BookStore } from './store.js';

const port = Number(process.env.PORT ?? 3000);
if (!Number.isInteger(port) || port < 0 || port > 65535) {
  throw new Error('PORT must be an integer between 0 and 65535');
}
const store = new BookStore(process.env.DB_PATH ?? 'books.sqlite');
const server = createApp(store).listen(port, () => {
  console.log(`Book API listening on port ${(server.address() as { port: number }).port}`);
});
server.on('error', (error) => {
  console.error(error);
  store.close();
  process.exitCode = 1;
});
for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.once(signal, () => {
    server.close(() => store.close());
  });
}
