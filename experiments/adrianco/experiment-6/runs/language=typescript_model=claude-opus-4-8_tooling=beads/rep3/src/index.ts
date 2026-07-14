import { createApp } from "./app.js";
import { createDb } from "./db.js";

const PORT = Number(process.env.PORT ?? 3000);
const DB_FILE = process.env.DB_FILE ?? "books.db";

const db = createDb(DB_FILE);
const app = createApp(db);

const server = app.listen(PORT, () => {
  console.log(`Book Collection API listening on http://localhost:${PORT}`);
});

function shutdown() {
  server.close(() => {
    db.close();
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
