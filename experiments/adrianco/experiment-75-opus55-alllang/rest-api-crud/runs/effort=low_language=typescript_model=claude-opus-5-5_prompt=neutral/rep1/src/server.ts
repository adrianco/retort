import { createApp } from "./app.js";

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? "books.db";
createApp(dbPath).listen(port, () => console.log(`Book API listening on http://localhost:${port}`));
