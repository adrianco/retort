import { expect } from 'chai';
import sqlite3 from 'sqlite3';
import { Database, open } from 'sqlite';

async function setupDatabase() {
  const db = await open({
    filename: './test-books.db',
    driver: sqlite3.Database
  });
  await db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  await db.close();
  
  return db;
}

async function createBook(db: Database, title: string, author: string, year?: number, isbn?: string) {
  const result = await db.run(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
    [title, author, year, isbn]
  );
  return result.lastID as number;
}

async function getAllBooks(db: Database, author?: string) {
  let query = 'SELECT * FROM books';
  let params: any[] = [];
  
  if (author) {
    query += ' WHERE author = ?';
    params.push(author);
  }
  
  const result = await db.all(query, params);
  return result;
}

async function getBookById(db: Database, id: number) {
  const result = await db.get('SELECT * FROM books WHERE id = ?', [id]);
  return result;
}

async function updateBook(db: Database, id: number, title?: string, author?: string, year?: number, isbn?: string) {
  let query = 'UPDATE books SET ';
  const params: any[] = [];
  const updates: string[] = [];
  
  if (title !== undefined) {
    updates.push('title = ?');
    params.push(title);
  }
  if (author !== undefined) {
    updates.push('author = ?');
    params.push(author);
  }
  if (year !== undefined) {
    updates.push('year = ?');
    params.push(year);
  }
  if (isbn !== undefined) {
    updates.push('isbn = ?');
    params.push(isbn);
  }
  
  query += updates.join(', ') + ' WHERE id = ?';
  params.push(id);
  
  await db.run(query, params);
}

async function deleteBook(db: Database, id: number) {
  await db.run('DELETE FROM books WHERE id = ?', [id]);
}

describe('Database Operations', function () {
  this.timeout(5000); // Increase timeout for database operations
  
  let db: Database;
  
  before(async () => {
    db = await open({
      filename: './test-books.db',
      driver: sqlite3.Database
    });
    await db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
  });
  
  beforeEach(async () => {
    // Clean up before each test
    await db.exec('DELETE FROM books');
  });
  
  after(async () => {
    await db.close();
  });
  
  it('should create a book', async () => {
    const id = await createBook(db, 'Test Book', 'Test Author', 2023, '123-4567890123');
    const book = await getBookById(db, id);
    expect(book).to.exist;
    expect(book.title).to.equal('Test Book');
    expect(book.author).to.equal('Test Author');
    expect(book.year).to.equal(2023);
    expect(book.isbn).to.equal('123-4567890123');
  });
  
  it('should get all books', async () => {
    await createBook(db, 'First Book', 'First Author', 2022);
    await createBook(db, 'Second Book', 'Second Author', 2021);
    const books = await getAllBooks(db);
    expect(books).to.have.lengthOf(2);
  });
  
  it('should filter books by author', async () => {
    await createBook(db, 'Test Book', 'Test Author', 2023);
    await createBook(db, 'Another Book', 'Another Author', 2022);
    const books = await getAllBooks(db, 'Test Author');
    expect(books).to.have.lengthOf(1);
    expect(books[0].title).to.equal('Test Book');
  });
  
  it('should update a book', async () => {
    const id = await createBook(db, 'Original Title', 'Original Author', 2020);
    await updateBook(db, id, 'Updated Title', 'Updated Author', 2024);
    const updatedBook = await getBookById(db, id);
    expect(updatedBook.title).to.equal('Updated Title');
    expect(updatedBook.author).to.equal('Updated Author');
    expect(updatedBook.year).to.equal(2024);
  });
  
  it('should delete a book', async () => {
    const id = await createBook(db, 'Book to Delete', 'Delete Author', 2020);
    await createBook(db, 'Book to Keep', 'Keep Author', 2021);
    
    await deleteBook(db, id);
    const remainingBooks = await getAllBooks(db);
    expect(remainingBooks).to.have.lengthOf(1);
    expect(remainingBooks[0].title).to.equal('Book to Keep');
  });
});
