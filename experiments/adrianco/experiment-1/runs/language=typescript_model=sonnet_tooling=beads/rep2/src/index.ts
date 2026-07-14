import { createApp } from './app';
import { getDb } from './database';

const PORT = process.env.PORT || 3000;
const db = getDb();
const app = createApp(db);

app.listen(PORT, () => {
  console.log(`Book collection API listening on port ${PORT}`);
});
