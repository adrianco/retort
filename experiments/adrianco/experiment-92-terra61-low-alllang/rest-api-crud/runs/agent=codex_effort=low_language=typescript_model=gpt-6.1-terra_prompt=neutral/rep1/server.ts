import { createApp } from './app.js';

const port = Number(process.env.PORT ?? 3000);
if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('PORT must be an integer between 0 and 65535');
const server = createApp(process.env.DB_PATH ?? 'books.sqlite');
server.listen(port, () => console.log(`Book API listening on port ${port}`));
