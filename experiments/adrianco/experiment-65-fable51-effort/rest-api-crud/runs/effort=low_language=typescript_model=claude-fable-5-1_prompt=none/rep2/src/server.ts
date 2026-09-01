import { createApp } from "./app";
import { createDb } from "./db";

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? "books.db";

const db = createDb(dbPath);
const app = createApp(db);

const server = app.listen(port, () => {
  console.log(`books-api listening on http://localhost:${port} (db: ${dbPath})`);
});

function shutdown() {
  server.close(() => {
    db.close();
    process.exit(0);
  });
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
