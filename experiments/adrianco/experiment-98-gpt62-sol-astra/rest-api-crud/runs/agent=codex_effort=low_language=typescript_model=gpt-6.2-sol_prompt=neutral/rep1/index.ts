import { createBookServer } from './books.js';

const port = Number(process.env.PORT ?? '3000');
const server = createBookServer(process.env.DATABASE_PATH ?? 'books.sqlite');

server.listen(port, () => {
  const address = server.address();
  if (address && typeof address === 'object') {
    console.log(`Book API listening on port ${address.port}`);
  }
});

for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.once(signal, () => server.close());
}
