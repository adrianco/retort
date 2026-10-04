import { createApp } from "./app.js";
import { BookStore } from "./db.js";

const port = Number(process.env.PORT ?? 3000);
const store = new BookStore(process.env.DB_PATH ?? "books.db");

createApp(store).listen(port, () => {
  console.log(`books-api listening on http://localhost:${port}`);
});
