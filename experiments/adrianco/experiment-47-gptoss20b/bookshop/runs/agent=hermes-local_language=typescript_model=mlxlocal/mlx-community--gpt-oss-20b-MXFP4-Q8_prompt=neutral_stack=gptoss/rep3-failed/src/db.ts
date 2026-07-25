import { Low, JSONFile } from 'lowdb';
import path from 'path';

const dbFile = path.join(__dirname, '..', 'data', 'books.json');
const adapter = new JSONFile(dbFile);
const db = new Low(adapter);

async function init() {
  await db.read();
  db.data ||= { books: [] };
  await db.write();
}

export { init, db };
