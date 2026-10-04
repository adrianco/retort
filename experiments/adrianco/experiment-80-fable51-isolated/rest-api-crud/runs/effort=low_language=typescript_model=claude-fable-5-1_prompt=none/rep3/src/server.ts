import { createApp } from "./app.js";

const port = Number(process.env.PORT ?? 3000);
const app = createApp(process.env.DB_PATH ?? "books.db");

app.listen(port, () => {
  console.log(`Books API listening on http://localhost:${port}`);
});
