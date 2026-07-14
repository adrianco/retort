import { createApp } from "./app.js";
import { createDb } from "./db.js";

const PORT = Number(process.env.PORT ?? 3000);
const DB_PATH = process.env.DB_PATH ?? "books.db";

const db = createDb(DB_PATH);
const app = createApp(db);

app.listen(PORT, () => {
  console.log(`Book collection API listening on http://localhost:${PORT}`);
});
