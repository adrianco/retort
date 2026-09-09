import { createApp } from './api.js';
const port = Number(process.env.PORT ?? 3000);
if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('PORT must be an integer between 0 and 65535');
const server = createApp(process.env.DB_PATH ?? 'books.sqlite');
server.listen(port, process.env.HOST ?? '127.0.0.1', () => {
  console.log(`Book API listening on ${JSON.stringify(server.address())}`);
});
for (const signal of ['SIGINT', 'SIGTERM'] as const) process.once(signal, () => server.close());
