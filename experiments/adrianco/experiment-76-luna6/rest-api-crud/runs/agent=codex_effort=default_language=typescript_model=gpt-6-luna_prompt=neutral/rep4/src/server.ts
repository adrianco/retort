import { createApp } from './app.ts';

const port = Number(process.env.PORT ?? 3000);
const server = createApp();
server.listen(port, () => console.log(`Book API listening on port ${port}`));

function shutdown() {
  server.close(() => process.exit(0));
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
