import { createApp } from "./app.js";

const port = Number(process.env.PORT ?? 8000);
const dbPath = process.env.DB_PATH ?? "books.db";

const app = createApp(dbPath);

app.listen(port, () => {
  console.log(`Book API listening on http://localhost:${port} (db: ${dbPath})`);
});
