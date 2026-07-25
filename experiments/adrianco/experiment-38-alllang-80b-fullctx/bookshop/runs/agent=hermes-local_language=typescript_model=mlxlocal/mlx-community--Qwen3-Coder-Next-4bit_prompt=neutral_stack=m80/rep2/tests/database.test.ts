import { BookDatabase } from '../src/database/database';

describe('BookDatabase', () => {
  let db: BookDatabase;

  beforeEach(async () => {
    db = new BookDatabase(':memory:');
    await db.initialize();
  });

  afterEach(async () => {
    await db.close();
  });

  describe('createBook', () => {
    it('should create a new book', async () => {
      const book = await db.createBook({
        title: 'Test Book',
        author: 'Test Author',
        year: 2024,
        isbn: '1234567890',
      });

      expect(book).toHaveProperty('id');
      expect(book.title).toBe('Test Book');
      expect(book.author).toBe('Test Author');
      expect(book.year).toBe(2024);
      expect(book.isbn).toBe('1234567890');
    });

    it('should create a book with optional fields', async () => {
      const book = await db.createBook({
        title: 'Minimal Book',
        author: 'Minimal Author',
      });

      expect(book).toHaveProperty('id');
      expect(book.title).toBe('Minimal Book');
      expect(book.author).toBe('Minimal Author');
      expect(book.year).toBeUndefined();
      expect(book.isbn).toBeUndefined();
    });
  });

  describe('getAllBooks', () => {
    it('should return all books', async () => {
      await db.createBook({
        title: 'Book 1',
        author: 'Author A',
        year: 2020,
        isbn: '111',
      });
      await db.createBook({
        title: 'Book 2',
        author: 'Author B',
        year: 2021,
        isbn: '222',
      });

      const books = await db.getAllBooks();
      expect(books.length).toBe(2);
    });

    it('should filter books by author', async () => {
      await db.createBook({
        title: 'Book 1',
        author: 'Author A',
        year: 2020,
        isbn: '111',
      });
      await db.createBook({
        title: 'Book 2',
        author: 'Author B',
        year: 2021,
        isbn: '222',
      });

      const books = await db.getAllBooks('Author A');
      expect(books.length).toBe(1);
      expect(books[0].author).toBe('Author A');
    });
  });

  describe('getBookById', () => {
    it('should return a book by ID', async () => {
      const book = await db.createBook({
        title: 'Get Book',
        author: 'Get Author',
        year: 2022,
        isbn: '999',
      });

      const retrieved = await db.getBookById(book.id);
      expect(retrieved).not.toBeNull();
      expect(retrieved?.id).toBe(book.id);
      expect(retrieved?.title).toBe('Get Book');
    });

    it('should return null for non-existent book', async () => {
      const book = await db.getBookById(99999);
      expect(book).toBeNull();
    });
  });

  describe('updateBook', () => {
    it('should update a book', async () => {
      const book = await db.createBook({
        title: 'Original Title',
        author: 'Original Author',
        year: 2020,
        isbn: '987',
      });

      const updated = await db.updateBook(book.id, {
        title: 'Updated Title',
        author: 'Updated Author',
      });

      expect(updated).not.toBeNull();
      expect(updated?.id).toBe(book.id);
      expect(updated?.title).toBe('Updated Title');
      expect(updated?.author).toBe('Updated Author');
      expect(updated?.year).toBe(2020); // unchanged
      expect(updated?.isbn).toBe('987'); // unchanged
    });

    it('should return null for non-existent book', async () => {
      const updated = await db.updateBook(99999, {
        title: 'Updated',
      });
      expect(updated).toBeNull();
    });
  });

  describe('deleteBook', () => {
    it('should delete a book', async () => {
      const book = await db.createBook({
        title: 'To Delete',
        author: 'Delete Author',
        year: 2023,
        isbn: '555',
      });

      const deleted = await db.deleteBook(book.id);
      expect(deleted).toBe(true);

      // Verify deletion
      const retrieved = await db.getBookById(book.id);
      expect(retrieved).toBeNull();
    });

    it('should return false for non-existent book', async () => {
      const deleted = await db.deleteBook(99999);
      expect(deleted).toBe(false);
    });
  });
});
