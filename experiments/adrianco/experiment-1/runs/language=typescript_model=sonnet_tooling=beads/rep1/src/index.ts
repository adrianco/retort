import { createApp } from './app';
import { createDb } from './db';

const db = createDb();
const app = createApp(db);
const port = process.env.PORT ?? 3000;

app.listen(port, () => {
  console.log(`Book API listening on port ${port}`);
});
