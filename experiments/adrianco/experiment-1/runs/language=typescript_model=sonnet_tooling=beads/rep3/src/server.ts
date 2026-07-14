import { createApp } from './app';
import { db } from './db';

const PORT = process.env.PORT || 3000;
const app = createApp(db);

app.listen(PORT, () => {
  console.log(`Book collection API running on port ${PORT}`);
});
