import { createApp } from "./app";
import { createDatabase } from "./db";

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const DB_FILE = process.env.DB_FILE ?? "books.db";

const db = createDatabase(DB_FILE);
const app = createApp(db);

app.listen(PORT, () => {
  console.log(`Book collection API listening on port ${PORT}`);
});
