import { createApp } from "./app.js";
import { BookRepository } from "./db.js";

const port = Number(process.env.PORT ?? 3000);
const repo = new BookRepository(process.env.DB_PATH ?? "books.db");
createApp(repo).listen(port, () => console.log(`Books API listening on http://localhost:${port}`));
