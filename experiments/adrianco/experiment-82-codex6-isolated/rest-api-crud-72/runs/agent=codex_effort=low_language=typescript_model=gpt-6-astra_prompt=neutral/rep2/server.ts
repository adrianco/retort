import { createApp } from './app.js';

const port = Number(process.env.PORT ?? 3000);
if (!Number.isInteger(port) || port < 0 || port > 65535) {
  throw new Error('PORT must be an integer between 0 and 65535');
}
const { app, close } = createApp(process.env.DB_PATH ?? 'books.sqlite');
const server = app.listen(port, () => {
  console.log(`Book API listening on port ${(server.address() as { port: number }).port}`);
});
server.on('error', (error) => {
  console.error(error);
  close();
  process.exitCode = 1;
});
let stopping = false;
function shutdown() {
  if (stopping) return;
  stopping = true;
  server.close(() => { close(); });
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
