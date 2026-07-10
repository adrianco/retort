"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getDb = getDb;
exports.initDb = initDb;
const sqlite3_1 = __importDefault(require("sqlite3"));
const sqlite_1 = require("sqlite");
// Open a connection to the SQLite database
async function getDb() {
    return (0, sqlite_1.open)({
        filename: './books.db',
        driver: sqlite3_1.default.Database
    });
}
// Initialize the database with the books table
async function initDb() {
    const db = await getDb();
    await db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )
  `);
    return db;
}
//# sourceMappingURL=database.js.map