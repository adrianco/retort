import { createApp } from "./app.js";

const port = Number(process.env.PORT ?? 3000);
createApp(process.env.DB_PATH ?? "books.db").listen(port, () => console.log(`Listening on http://localhost:${port}`));
