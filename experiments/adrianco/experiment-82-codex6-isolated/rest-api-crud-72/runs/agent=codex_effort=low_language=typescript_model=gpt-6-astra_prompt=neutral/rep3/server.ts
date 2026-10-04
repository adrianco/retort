import { createApp } from './app.js';

const port = Number(process.env.PORT ?? 3000);
if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('Invalid PORT');
const { app, close } = createApp(process.env.DATABASE_PATH ?? 'books.sqlite');
const server = app.listen(port, () => {
  console.log(`Book API listening on port ${(server.address() as { port: number }).port}`);
});
server.on('error', (error) => { close(); console.error(error); process.exitCode = 1; });
for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.once(signal, () => { server.close(() => close()); });
}
