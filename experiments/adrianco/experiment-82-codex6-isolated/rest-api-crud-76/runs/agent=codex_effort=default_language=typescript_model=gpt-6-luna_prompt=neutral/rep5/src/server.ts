import { createApp } from './app.js';
import { createDatabase } from './db.js';

const db = createDatabase();
const port = Number(process.env.PORT ?? 3000);
createApp(db).listen(port, () => console.log(`Book API listening on port ${port}`));
