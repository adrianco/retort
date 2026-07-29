import { createApp } from "./app";
import { createDatabase } from "./db";

const database = createDatabase();
const port = Number(process.env.PORT ?? 3000);
const app = createApp(database);
app.listen(port, () => console.log(`Book API listening on port ${port}`));
