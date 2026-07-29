import { createApp } from './app.ts';

const port = Number(process.env.PORT ?? 3000);
const { server } = createApp(process.env.DATABASE_PATH ?? './books.sqlite');
server.listen(port, () => console.log(`Book API listening on port ${port}`));
