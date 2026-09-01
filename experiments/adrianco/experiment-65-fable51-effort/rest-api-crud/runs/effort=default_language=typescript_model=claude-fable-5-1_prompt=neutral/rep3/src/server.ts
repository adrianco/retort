import { createApp } from "./app.js";
import { BookRepository } from "./db.js";

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DATABASE_PATH ?? "books.db";

const repo = new BookRepository(dbPath);
const app = createApp(repo);

const server = app.listen(port, () => {
  console.log(`Books API listening on http://localhost:${port} (db: ${dbPath})`);
});

function shutdown(signal: string): void {
  console.log(`Received ${signal}, shutting down`);
  server.close(() => {
    repo.close();
    process.exit(0);
  });
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
