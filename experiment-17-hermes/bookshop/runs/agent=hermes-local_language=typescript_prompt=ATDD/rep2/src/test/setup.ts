import { DatabaseHelper } from '../database';

// Set up a separate test database
const testDb = new DatabaseHelper('test-books.db');

beforeAll(async () => {
  await testDb.init();
});

afterAll(async () => {
  // Clean up test database
  await testDb.db?.close();
});
