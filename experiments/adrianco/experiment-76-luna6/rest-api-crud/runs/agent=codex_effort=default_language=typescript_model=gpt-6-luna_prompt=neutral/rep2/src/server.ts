import { createBookServer } from './books';

const port = Number(process.env.PORT ?? 3000);
const app = createBookServer();
app.server.listen(port, () => console.log(`Book API listening on port ${port}`));
for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.on(signal, () => app.server.close(() => { app.close(); process.exit(0); }));
}
