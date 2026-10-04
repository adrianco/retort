import { createApp } from "./app";
import { BookStore } from "./db";

const port = Number(process.env.PORT ?? 3000);
const store = new BookStore(process.env.DB_PATH ?? "books.db");

createApp(store).listen(port, () => {
  console.log(`Books API listening on http://localhost:${port}`);
});
