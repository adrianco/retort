import { createApp } from "./app";
import { BookStore } from "./db";

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? "books.db";

const store = new BookStore(dbPath);
const server = createApp(store).listen(port, () => {
  console.log(`Books API listening on http://localhost:${port} (db: ${dbPath})`);
});

for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, () => {
    server.close(() => {
      store.close();
      process.exit(0);
    });
  });
}
